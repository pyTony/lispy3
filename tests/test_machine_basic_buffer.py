"""Run editor BASIC source through the actual mini-basic reader."""
from unittest.mock import Mock, patch
from unittest import TestCase
from test_machine_eval_buffer import _FakeMachine
from test_machine_args import machine
from support import fresh_global_env


class BasicBufferTest(TestCase):
    def setUp(self):
        fresh_global_env()

    def tearDown(self):
        machine.L.library_system.reset()
        fresh_global_env()

    def test_whole_buffer_runs_basic_with_quotes_and_backslashes(self):
        app = _FakeMachine('FOR I%=1 TO 3\nPRINT I%\nNEXT\nPRINT "C:\\demo"')
        app.eval_buffer = lambda **kwargs: machine.LispMachine.eval_buffer(app, **kwargs)
        machine.LispMachine.eval_basic_buffer(app)
        out = ''.join(app.lines)
        self.assertNotIn('Error:', out)
        self.assertIn('1\n2\n3\nC:\\demo', '\n'.join(line.strip() for line in out.splitlines()))

    def test_selection_is_used_when_present(self):
        app = _FakeMachine('not a whole BASIC program')
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ('1.0', '1.8')
        app.tab.text.get.return_value = 'PRINT 42'
        app.tab.text.index.return_value = '5.0'
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_at_cursor(app)
        app.eval_buffer.assert_called_once_with(basic=True, source='PRINT 42', source_line=1)

    def test_current_line_is_used_without_selection(self):
        app = _FakeMachine('PRINT 42')
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ()
        app.tab.text.get.return_value = 'PRINT 42'
        app.tab.text.index.return_value = '5.0'
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_at_cursor(app)
        app.tab.text.get.assert_called_once_with('insert linestart', 'insert lineend')
        app.eval_buffer.assert_called_once_with(basic=True, source='PRINT 42', source_line=5)

    def test_basic_buffer_timing_and_syntax_errors(self):
        # Library initialization also uses the clock for BASIC TIME.
        _FakeMachine('(import (prefix (only mini-basic bbc-run) editor-basic:))').run()
        app = _FakeMachine('FOR')
        app.tab.text = Mock()
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        with patch.object(machine.time, 'perf_counter', side_effect=[1.0, 1.25]):
            machine.LispMachine.eval_buffer(app, basic=True)
        out = ''.join(app.lines)
        self.assertIn('Error:', out)
        self.assertIn('0.250 s', out)
        app.tab.text.tag_add.assert_called_with('syntax_error', '1.0', '1.end')

    def test_python_backend_uses_unsaved_text_and_highlights_numbered_line(self):
        app = _FakeMachine('10 PRINT 1\n100 FOR')
        app.tab.text = Mock()
        app.basic_backend = Mock()
        app.basic_backend.get.return_value = 'python'
        app.basic_pygame = Mock()
        app.basic_pygame.get.return_value = False
        app.settings = {'basic_directory': '/configured/mini_basic'}
        def run(source, write, **kwargs):
            self.assertEqual(source, app.tab.content)
            self.assertEqual(kwargs['package_root'], '/configured/mini_basic')
            write('Error in line 100: expected variable\n')
            return 1
        with patch.object(machine.BR, 'run_python_basic', side_effect=run):
            machine.LispMachine.eval_buffer(app, basic=True)
        app.tab.text.tag_add.assert_called_with('syntax_error', '2.0', '2.end')

    def test_lispy_selected_error_maps_to_original_buffer_line(self):
        app = _FakeMachine('; before\n; before\nFOR')
        app.tab.text = Mock()
        machine.LispMachine.eval_buffer(app, basic=True, source='FOR', source_line=3)
        app.tab.text.tag_add.assert_called_with('syntax_error', '3.0', '3.end')
