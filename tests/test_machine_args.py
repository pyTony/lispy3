"""Tests for opening files named on the editor's command line.

tkinter is replaced by a stub when it is missing, so only the file handling
is tested here, not the window.

Run:  python -m unittest discover tests
"""
import contextlib
import importlib.machinery
import io
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

from support import REPO_DIR


class _Anything:
    """Stands in for any tkinter name: a base class, function or constant."""
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Anything


def _stub_tkinter():
    for name in ("tkinter", "tkinter.ttk", "tkinter.filedialog",
                 "tkinter.messagebox", "tkinter.scrolledtext"):
        module = types.ModuleType(name)
        module.__getattr__ = lambda attr: _Anything
        sys.modules[name] = module
    for child in ("ttk", "filedialog", "messagebox", "scrolledtext"):
        setattr(sys.modules["tkinter"], child, sys.modules["tkinter." + child])


def _load_machine():
    try:
        import tkinter  # noqa: F401
    except ImportError:
        _stub_tkinter()
    path = os.path.join(REPO_DIR, "lispy_machine.pyw")
    loader = importlib.machinery.SourceFileLoader("lispy_machine", path)
    spec = importlib.util.spec_from_loader("lispy_machine", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


machine = _load_machine()


class Version(unittest.TestCase):
    def test_version_option_prints_and_does_not_open_the_editor(self):
        """--version and -V print the version without opening the editor window."""
        for option in ("--version", "-V"):
            with mock.patch.object(sys, "argv", ["lispy_machine.pyw", option]), \
                    mock.patch.object(machine, "LispMachine") as app, \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                machine.main()
            app.assert_not_called()
            self.assertEqual(out.getvalue().strip(), machine.version_text())
            self.assertIn(f"Lispy3 Machine {machine.__version__}", out.getvalue())
            self.assertIn(f"lispy3 {machine.L.__version__}", out.getvalue())


class NumpyInterpreter(unittest.TestCase):
    def test_numpy_version_is_used_exactly_when_numpy_is_installed(self):
        """The Machine uses lispy3-numpy.py exactly when NumPy is installed."""
        try:
            import numpy  # noqa: F401
            has_numpy = True
        except ImportError:
            has_numpy = False
        self.assertEqual(machine.USING_NUMPY, has_numpy)
        self.assertEqual("vector-fill!" in machine.L.global_env, has_numpy)
        self.assertEqual("NumPy" in machine.version_text(), has_numpy)


class ReadFileArg(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_existing_file_gives_its_content(self):
        """A file named on the command line opens with its content."""
        path = os.path.join(self.dir.name, "demo.lisp")
        with open(path, "w", encoding="utf-8") as f:
            f.write("(+ 1 2)\n")
        self.assertEqual(machine.read_file_arg(path),
                         ("demo.lisp", "(+ 1 2)\n", path))

    def test_missing_file_gives_an_empty_buffer_with_that_path(self):
        """A file that does not exist yet opens as an empty buffer and is not created."""
        path = os.path.join(self.dir.name, "new.lisp")
        self.assertEqual(machine.read_file_arg(path), ("new.lisp", "", path))
        self.assertFalse(os.path.exists(path))

    def test_relative_path_is_made_absolute(self):
        """A relative path is turned into an absolute one."""
        cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.addCleanup(os.chdir, cwd)
        name, _, path = machine.read_file_arg("rel.lisp")
        self.assertEqual(name, "rel.lisp")
        self.assertTrue(os.path.isabs(path))
        self.assertEqual(os.path.basename(path), "rel.lisp")

class ReadDemo(unittest.TestCase):
    def test_startup_file_is_next_to_the_editor(self):
        """startup.lisp next to the editor opens as the first buffer."""
        self.assertEqual(machine.STARTUP_FILE, os.path.join(REPO_DIR, "startup.lisp"))
        name, content, path = machine.read_startup()
        self.assertEqual((name, path), ("startup.lisp", machine.STARTUP_FILE))
        with open(machine.STARTUP_FILE, encoding="utf-8") as f:
            self.assertEqual(content, f.read())

    def test_missing_startup_file_gives_an_empty_untitled_buffer(self):
        """Without startup.lisp the editor opens an empty untitled.lisp."""
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(machine.read_startup(os.path.join(d, "startup.lisp")),
                             ("untitled.lisp", "", None))

if __name__ == "__main__":
    unittest.main()
