"""Tk cycles must be collected by the GUI thread, never an allocating worker."""
import gc
import threading
from unittest import TestCase


class GuiCollectionTest(TestCase):
    def test_worker_allocations_do_not_finalize_gui_cycles(self):
        from lispy_support.gui_gc import GuiGarbageCollector
        events = []
        class Resource:
            def __del__(self):
                events.append(threading.current_thread())
        threshold = gc.get_threshold()
        try:
            with GuiGarbageCollector() as collector:
                resource = Resource()
                resource.cycle = resource
                del resource
                gc.set_threshold(5, 5, 5)
                def allocate():
                    for _ in range(10000):
                        cycle = []
                        cycle.append(cycle)
                worker = threading.Thread(target=allocate)
                worker.start(); worker.join()
                self.assertEqual(events, [])
                collector.collect()
                self.assertEqual(events, [threading.main_thread()])
        finally:
            gc.set_threshold(*threshold)

    def test_collection_and_state_restore_after_failure(self):
        from lispy_support.gui_gc import GuiGarbageCollector
        enabled = gc.isenabled()
        with self.assertRaisesRegex(ValueError, 'example'):
            with GuiGarbageCollector():
                self.assertFalse(gc.isenabled())
                raise ValueError('example')
        self.assertEqual(gc.isenabled(), enabled)

    def test_preserves_preexisting_disabled_gc(self):
        from lispy_support.gui_gc import GuiGarbageCollector
        enabled = gc.isenabled()
        gc.disable()
        try:
            with GuiGarbageCollector():
                pass
            self.assertFalse(gc.isenabled())
        finally:
            if enabled: gc.enable()
