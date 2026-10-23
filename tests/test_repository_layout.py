"""Repository layout and launcher portability."""
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock
from support import REPO_DIR


class RepositoryLayoutTest(TestCase):
    def test_python_helpers_are_packaged_away_from_root(self):
        root = Path(REPO_DIR)
        self.assertTrue((root / 'lispy_support' / '__init__.py').is_file())
        for name in ('basic_io', 'basic_repl', 'basic_runner', 'editor_tools', 'graphics_modes', 'gui_gc', 'guide', 'lispy_graphics', 'lispy_graphics_bindings', 'lispy_libraries', 'lispy_terminal', 'lispy_workspaces', 'listener_output', 'repl_completion', 'startup_options', 'syntax_highlight'):
            with self.subTest(module=name):
                self.assertTrue((root / 'lispy_support' / (name+'.py')).is_file())
                self.assertFalse((root / (name+'.py')).exists())
        for name in ('make_shortcut.py', 'run_complex_checks.py'):
            self.assertTrue((root / 'tools' / name).is_file())
            self.assertFalse((root / name).exists())

    def test_assets_and_basic_directory_still_resolve_from_project_root(self):
        from lispy_support import guide, syntax_highlight
        from lispy_support.basic_repl import BasicRepl
        root = Path(REPO_DIR)
        self.assertEqual(Path(guide.DOCS_DIR), root / 'docs')
        self.assertEqual(Path(syntax_highlight.SYNTAX_DIR), root / 'syntax')
        self.assertEqual(BasicRepl(SimpleNamespace(workspaces=Mock())).directory, root / 'basic')

    def test_existing_launchers_work_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            for launcher, option in [('lispy3.py', '--help'), ('lispy3-numpy.py', '--help'), ('lispy_machine.pyw', '--version')]:
                with self.subTest(launcher=launcher):
                    result = subprocess.run([sys.executable, str(Path(REPO_DIR)/launcher), option], cwd=directory, text=True, capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn('ModuleNotFoundError', result.stderr)
