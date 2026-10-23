from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine


class LispDirectoryTest(TestCase):
    def test_default_is_programs_directory(self):
        app = SimpleNamespace(settings={})
        self.assertEqual(machine.LispMachine._file_dialog_dir(app), str(Path(machine.L.LISP_DIR) / 'programs'))

    def test_configured_directory_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SimpleNamespace(settings={'lisp_programs_directory': directory})
            self.assertEqual(machine.LispMachine._file_dialog_dir(app), directory)

    def test_missing_configured_directory_falls_back_to_programs(self):
        app = SimpleNamespace(settings={'lisp_programs_directory': '/nonexistent/lispy-test-folder'})
        self.assertEqual(machine.LispMachine._file_dialog_dir(app), str(Path(machine.L.LISP_DIR) / 'programs'))

    def test_save_as_keeps_existing_file_directory(self):
        app = SimpleNamespace(settings={})
        path = str(Path(machine.APP_DIR) / 'other' / 'source.lisp')
        tab = SimpleNamespace(path=path, source_path=None)
        self.assertEqual(machine.LispMachine._file_dialog_dir(app, tab), str(Path(path).parent))

    def test_directory_choice_is_persisted(self):
        app = Mock()
        app.settings = {}
        with patch.object(machine.filedialog, 'askdirectory', return_value='chosen'), patch.object(machine, 'save_settings') as save:
            machine.LispMachine._choose_lisp_directory(app)
        self.assertEqual(app.settings['lisp_programs_directory'], 'chosen')
        save.assert_called_once_with(app.settings)
