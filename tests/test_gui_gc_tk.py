"""Real Tk regression in a child process, isolated from the headless test stubs."""
import os
import subprocess
import sys
from unittest import TestCase


PROBE = r'''
import gc, sys, threading, tkinter as tk, turtle
from gui_gc import GuiGarbageCollector
events = []
class Image(tk.PhotoImage):
    def __del__(self):
        events.append(threading.current_thread() is threading.main_thread())
        super().__del__()
def allocate():
    for _ in range(20000):
        cycle = []
        cycle.append(cycle)
try:
    root = tk.Tk()
except tk.TclError:
    sys.exit(77)
root.withdraw()
with GuiGarbageCollector() as collector:
    for _ in range(3):
        turtle.TurtleScreen._RUNNING = True
        screen = turtle.Screen()
        screen._root.withdraw()
        turtle.forward(1)
        screen.bye()
        del screen
        image = Image(master=root, width=1, height=1)
        image.cycle = image
        del image
        gc.set_threshold(5, 5, 5)
        worker = threading.Thread(target=allocate)
        worker.start(); worker.join()
        assert not events
        collector.collect()
        assert events == [True], events
        events.clear()
    root.destroy()
    del root
print('Tk cleanup stayed on main thread')
'''


class RealTkCleanupTest(TestCase):
    def test_closed_turtle_and_image_cycles_survive_worker_allocations(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, '-c', PROBE], cwd=root,
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 77:
            self.skipTest('Tk display unavailable')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Exception ignored', result.stderr)
        self.assertNotIn('Tcl_AsyncDelete', result.stderr)
        self.assertIn('Tk cleanup stayed on main thread', result.stdout)
