"""Tests for opening files named on the editor's command line.

tkinter is replaced by a stub when it is missing, so only the file handling
is tested here, not the window.

Run:  python -m unittest discover tests
"""
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import types
import unittest

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


class ReadFileArg(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_existing_file_gives_its_content(self):
        path = os.path.join(self.dir.name, "demo.lisp")
        with open(path, "w", encoding="utf-8") as f:
            f.write("(+ 1 2)\n")
        self.assertEqual(machine.read_file_arg(path),
                         ("demo.lisp", "(+ 1 2)\n", path))

    def test_missing_file_gives_an_empty_buffer_with_that_path(self):
        path = os.path.join(self.dir.name, "new.lisp")
        self.assertEqual(machine.read_file_arg(path), ("new.lisp", "", path))
        self.assertFalse(os.path.exists(path))

    def test_relative_path_is_made_absolute(self):
        cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.addCleanup(os.chdir, cwd)
        name, _, path = machine.read_file_arg("rel.lisp")
        self.assertEqual(name, "rel.lisp")
        self.assertTrue(os.path.isabs(path))
        self.assertEqual(os.path.basename(path), "rel.lisp")

    def test_bare_name_not_here_opens_the_one_in_lisp_folder(self):
        cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.addCleanup(os.chdir, cwd)
        name, content, path = machine.read_file_arg("tree.lisp")
        self.assertEqual(path, os.path.join(machine.L.LISP_DIR, "tree.lisp"))
        self.assertIn('(load "lsystems")', content)
        _, _, path = machine.read_file_arg("brand_new.lisp")
        self.assertEqual(path, os.path.join(machine.L.LISP_DIR, "brand_new.lisp"))
        self.assertFalse(os.path.exists(path))

    def test_a_folder_is_an_error(self):
        with self.assertRaises(OSError):
            machine.read_file_arg(self.dir.name)


class ReadDemo(unittest.TestCase):
    def test_demo_file_is_in_the_lisp_folder(self):
        self.assertEqual(machine.DEMO_FILE, os.path.join(REPO_DIR, "lisp", "demo.lisp"))
        name, content, path = machine.read_demo()
        self.assertEqual((name, path), ("demo.lisp", machine.DEMO_FILE))
        with open(machine.DEMO_FILE, encoding="utf-8") as f:
            self.assertEqual(content, f.read())

    def test_missing_demo_gives_an_empty_untitled_buffer(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(machine.read_demo(os.path.join(d, "demo.lisp")),
                             ("untitled.lisp", "", None))


if __name__ == "__main__":
    unittest.main()
