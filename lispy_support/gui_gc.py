"""Keep cyclic Tk finalizers on the thread that owns the GUI.

Automatic cyclic GC runs on whichever thread triggers its allocation threshold.
After a turtle window closes its unreachable Tk/image cycles can otherwise be
collected by Lisp evaluation. Reference counting stays enabled; only cyclic
collection is scheduled explicitly on the main thread while the GUI is active.
"""
import gc
import threading


class GuiGarbageCollector:
    def __enter__(self):
        self._check_thread()
        self._enabled = gc.isenabled()
        self._active = True
        self._root = None
        self._timer = None
        gc.disable()
        return self

    @staticmethod
    def _check_thread():
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('GUI collection requires the main thread')

    def collect(self):
        self._check_thread()
        return gc.collect()

    def schedule(self, root):
        self._check_thread()
        self._root = root
        self._timer = root.after(1000, self._tick)

    def _tick(self):
        if self._active:
            self.collect()
            self.schedule(self._root)

    def __exit__(self, *exception):
        self._check_thread()
        self._active = False
        if self._root is not None and self._timer is not None:
            try:
                self._root.after_cancel(self._timer)
            except Exception:
                pass  # The root may already have been destroyed.
        self._root = None
        try:
            self.collect()
        finally:
            if self._enabled:
                gc.enable()
