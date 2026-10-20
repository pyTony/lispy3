"""Tests for running Lisp off the Tk thread in the Lispy Machine, and for Stop.

The window is not opened: a small stand-in plays the Tk thread, running the
calls the Lisp thread hands it as the window's event loop would.

Run:  python -m unittest discover tests
"""
import threading
import time
import unittest

from support import fresh_global_env, lispy3 as L
import turtle_stub
from test_machine_args import machine


class _FakeMachine:
    """Just enough of LispMachine for _start, _pump, stop and the GUI built-ins."""
    for _name in ("_start", "_pump", "_finish", "_ui", "_ui_post", "_busy", "_sleep",
                  "_gui_builtins_on_main", "_on_main_fn", "_gui_call", "_run",
                  "_eval_with_turtle"):
        locals()[_name] = getattr(machine.LispMachine, _name)
    del _name

    def __init__(self):
        self._job = None
        self._calls = machine.queue.Queue()
        self._pending = []           # after() callbacks
        self.lines = []
        self.running_states = []
        self.results = []
        self.ui_threads = set()      # threads the GUI built-ins ran on

    def after(self, ms, fn):
        self._pending.append(fn)

    def _set_running(self, running):
        self.running_states.append(running)

    def listener_write(self, text, tag=None):
        self.lines.append(text)

    def set_inspector(self, text):
        pass

    def stop(self):
        machine.stop_thread(self._job)

    def done(self, result, stopped):
        self.results.append((result, stopped))

    def loop(self, seconds=5.0, stop_after=None):
        """The Tk event loop: run after() callbacks until the job ends."""
        start = time.monotonic()
        while self._job is not None and time.monotonic() - start < seconds:
            if stop_after is not None and time.monotonic() - start > stop_after:
                self.stop()
                stop_after = None
            pending, self._pending = self._pending, []
            for fn in pending:
                fn()
        return self._job is None


class LispThreadTest(unittest.TestCase):

    def setUp(self):
        fresh_global_env()
        self.app = _FakeMachine()
        L.global_env['sleep'] = self.app._sleep

    def run_code(self, code, stop_after=None):
        self.assertTrue(self.app._start(lambda: self.app._run(code), self.app.done))
        self.assertTrue(self.app.loop(stop_after=stop_after), "the Lisp thread did not finish")
        return self.app.results[-1]

    def test_result_comes_back(self):
        """Code runs on the Lisp thread and its value reaches the Tk thread."""
        (val, err), stopped = self.run_code("(+ 1 2)")
        self.assertEqual((val, err, stopped), (3, None, False))
        self.assertEqual(self.app.running_states, [True, False])

    def test_stop_ends_an_endless_loop(self):
        """Stop ends (while #t ...) and the machine is ready again."""
        result, stopped = self.run_code("(begin (define n 0) (while #t (set! n (+ n 1))))", stop_after=0.3)
        self.assertTrue(stopped)
        self.assertIn(";; Stopped.\n", self.app.lines)
        self.assertGreater(L.global_env['n'], 0)
        (val, err), stopped = self.run_code("(* 6 7)")
        self.assertEqual((val, stopped), (42, False))

    def test_try_does_not_catch_stop(self):
        """(try ...) catches Lisp errors but not Stop."""
        result, stopped = self.run_code("(while #t (try (+ 1 1) (catch e 0)))", stop_after=0.3)
        self.assertTrue(stopped)

    def test_stop_cuts_sleep_short(self):
        """Stop does not wait for (sleep 30) to end."""
        start = time.monotonic()
        result, stopped = self.run_code("(sleep 30)", stop_after=0.2)
        self.assertTrue(stopped)
        self.assertLess(time.monotonic() - start, 3)

    def test_only_one_run_at_a_time(self):
        """A second evaluation is refused while the first still runs."""
        self.assertTrue(self.app._start(lambda: self.app._run("(sleep 0.3)"), self.app.done))
        self.assertFalse(self.app._start(lambda: self.app._run("1"), self.app.done))
        self.assertIn("Still running", "".join(self.app.lines))
        self.assertTrue(self.app.loop())

    def test_output_reaches_the_listener(self):
        """display on the Lisp thread is written to the Listener by the Tk thread."""
        self.run_code('(begin (display "hi") (display "there"))')
        self.assertIn("hi", "".join(self.app.lines))

    def test_turtle_runs_on_the_tk_thread(self):
        """Turtle built-ins are handed to the Tk thread, in order."""
        main = threading.current_thread()
        seen = []
        real_fd = turtle_stub.fd
        turtle_stub.fd = lambda *a: seen.append((threading.current_thread(), a))
        try:
            fresh_global_env()
            self.app._gui_builtins_on_main()
            self.run_code("(dotimes (i 3) (fd i))")
        finally:
            turtle_stub.fd = real_fd
        self.assertEqual([a for _, a in seen], [(0,), (1,), (2,)])
        self.assertEqual({t for t, _ in seen}, {main})


if __name__ == "__main__":
    unittest.main()
