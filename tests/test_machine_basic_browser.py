from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from test_machine_args import machine


class BasicBrowserTest(TestCase):
    def test_configured_directory_then_last_loaded_then_examples(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            configured = root / 'configured'
            previous = root / 'previous'
            examples = root / 'examples'
            for path in (configured, previous, examples):
                path.mkdir()
            app = Mock(settings={'basic_examples_directory': str(configured),
                                 'basic_last_directory': str(previous),
                                 'basic_directory': str(root)})
            self.assertEqual(machine.LispMachine._basic_dialog_dir(app), str(configured))
            configured.rmdir()
            self.assertEqual(machine.LispMachine._basic_dialog_dir(app), str(previous))
            previous.rmdir()
            self.assertEqual(machine.LispMachine._basic_dialog_dir(app), str(examples))

    def test_cancel_does_not_switch_mode_or_load(self):
        app = Mock()
        app._busy.return_value = False
        with patch.object(machine.filedialog, 'askopenfilename', return_value=''):
            machine.LispMachine.load_basic(app)
        app._select_listener_mode.assert_not_called()
        app._basic_feed.assert_not_called()

    def test_selection_uses_existing_load_command(self):
        app = Mock()
        app._busy.return_value = False
        with patch.object(machine.filedialog, 'askopenfilename', return_value='C:/BASIC/demo.bas'):
            machine.LispMachine.load_basic(app)
        app.listener_mode.set.assert_called_once_with('basic')
        app._select_listener_mode.assert_called_once()
        app._basic_feed.assert_called_once_with(['LOAD "C:/BASIC/demo.bas"'])
