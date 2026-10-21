from unittest import TestCase
from unittest.mock import patch, Mock
from pathlib import Path
import tempfile
import basic_runner as BR

class BBCSDLRunnerTest(TestCase):
    def test_unsaved_source_is_passed_to_native_helper_until_window_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder)/"bbcsdl.exe"; exe.touch()
            helper = Path(folder)/"basrun.bbc"; helper.write_bytes(b"native")
            def launch(command, **kwargs):
                self.assertEqual(command[:2], [str(exe), str(helper)])
                self.assertEqual(Path(command[2]).read_text(), 'PRINT "unsaved"')
                self.assertEqual(kwargs['cwd'], folder)
                process = Mock(); process.wait.return_value = 0
                return process
            with patch.object(BR.subprocess, 'Popen', side_effect=launch):
                self.assertEqual(BR.run_bbcsdl('PRINT "unsaved"', cwd=folder, executable=str(exe), helper=str(helper)), 0)
    def test_missing_helper_has_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, 'basrun.bbc'):
            BR.run_bbcsdl('PRINT 1', cwd='.', executable=__file__, helper='missing-basrun.bbc')

    def test_stop_reaps_only_its_native_child(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder)/'bbcsdl'; exe.touch()
            helper = Path(folder)/'basrun.bbc'; helper.touch()
            process = Mock(); process.poll.return_value = None
            process.wait.side_effect = [KeyboardInterrupt(), 0]
            with patch.object(BR.subprocess, 'Popen', return_value=process):
                with self.assertRaises(KeyboardInterrupt):
                    BR.run_bbcsdl('PRINT 1', cwd=folder, executable=str(exe), helper=str(helper))
            process.terminate.assert_called_once()
            self.assertEqual(process.wait.call_count, 2)

    def test_editor_runs_unsaved_buffer_in_native_window(self):
        from test_machine_args import machine
        app = Mock(); tab = app.current_tab.return_value
        tab.get_content.return_value = 'PRINT "current edits"'
        tab.path = str(Path(__file__).resolve())
        app._busy.return_value = False
        app.settings = {'bbcsdl_executable': 'native-exe', 'bbcsdl_helper': 'native-helper'}
        app._start.side_effect = lambda run: run()
        with patch.object(BR, 'run_bbcsdl', return_value=0) as run:
            machine.LispMachine.eval_bbcsdl_buffer(app)
        run.assert_called_once_with('PRINT "current edits"', cwd=str(Path(__file__).resolve().parent),
                                    executable='native-exe', helper='native-helper')
