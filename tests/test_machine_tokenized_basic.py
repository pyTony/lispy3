from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch
from test_machine_args import machine
import basic_runner as BR

class TokenizedBasicTest(TestCase):
    def test_bbc_opens_as_unsaved_basic_using_configured_mini_basic(self):
        app = Mock(); app.tabs = {}; app.settings = {'basic_python': 'configured-python', 'basic_directory': '/mini'}
        path = str(Path('example.BBC').resolve())
        with patch.object(BR, 'detokenize_bbc', return_value='10 PRINT "hello"\n') as decode:
            machine.LispMachine._open_source_path(app, path)
        decode.assert_called_once_with(path, executable='configured-python', package_root='/mini')
        app.new_buffer.assert_called_once_with('example.bas', '10 PRINT "hello"\n', path=None)
        self.assertEqual(app.new_buffer.return_value.source_path, path)

    def test_import_error_opens_no_partial_buffer(self):
        app = Mock(); app.tabs = {}; app.settings = {}
        with patch.object(BR, 'detokenize_bbc', side_effect=RuntimeError('Invalid BBC program')), patch.object(machine.messagebox, 'showerror') as error:
            machine.LispMachine._open_source_path(app, 'broken.bbc')
        app.new_buffer.assert_not_called()
        self.assertIn('Invalid BBC program', error.call_args.args[1])

    def test_binary_cannot_be_overwritten_with_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'original.BBC'; path.write_bytes(b'native bytes')
            tab = Mock(); tab.get_content.return_value = 'PRINT 1'
            with patch.object(machine.messagebox, 'showerror'):
                self.assertFalse(machine.LispMachine._save_tab_to_path(Mock(), tab, str(path)))
            self.assertEqual(path.read_bytes(), b'native bytes')

    def test_open_filter_includes_both_tokenized_extensions(self):
        patterns = machine.source_filetypes()[0][1]
        self.assertIn('*.bbc', patterns); self.assertIn('*.BBC', patterns)

    def test_command_line_input_uses_the_same_decoder(self):
        with patch.object(BR, 'detokenize_bbc', return_value='10 END\n'):
            self.assertEqual(machine.read_file_arg('cli.BBC'), ('cli.bas', '10 END\n', None))

    def test_subprocess_reuses_public_decoder_without_running_basic(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)/'mini_basic'; package.mkdir()
            (package/'__init__.py').write_text('')
            (package/'bbc_detokenize.py').write_text(
                'def bbc_binary_to_source(data):\n'
                '    if data != b"native": raise ValueError("invalid BBC binary")\n'
                "    return ['10 PRINT \"decoded\"', '20 END']\n")
            source = Path(directory)/'input.BBC'; source.write_bytes(b'native')
            self.assertEqual(BR.detokenize_bbc(source, package_root=directory), '10 PRINT "decoded"\n20 END\n')
            source.write_bytes(b'invalid')
            with self.assertRaisesRegex(RuntimeError, 'invalid BBC binary'):
                BR.detokenize_bbc(source, package_root=directory)

    def test_missing_decoder_reports_basic_settings(self):
        import subprocess
        with patch.object(BR, 'default_package_root', return_value=''), patch.object(BR.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 1, '', "ModuleNotFoundError: No module named 'mini_basic'")):
            with self.assertRaisesRegex(RuntimeError, 'BASIC Settings'):
                BR.detokenize_bbc('input.bbc')

    def test_reopening_import_preserves_existing_edits(self):
        app = Mock(); tab = Mock(); tab.path = None
        tab.source_path = str(Path('original.bbc').resolve())
        app.tabs = {'original.bas': tab}
        with patch.object(BR, 'detokenize_bbc') as decode:
            machine.LispMachine._open_source_path(app, tab.source_path)
        decode.assert_not_called()
        app.new_buffer.assert_not_called()
        app.notebook.select.assert_called_once_with(tab)

    def test_command_line_import_retains_its_source_directory(self):
        app = Mock(); app.tabs = {}; app.settings = {}
        path = str(Path('reference/program.BBC').resolve())
        app.new_buffer.side_effect = lambda *args, **kwargs: app.tabs.setdefault(args[0], Mock())
        with patch.object(BR, 'detokenize_bbc', return_value='10 END\n'):
            errors = machine.LispMachine._open_initial_buffers(app, [path])
        self.assertEqual(errors, [])
        imported = app.tabs['program.bas']
        imported.path = None
        self.assertEqual(machine.buffer_source_path(imported), path)
