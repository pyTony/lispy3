"""Run editor BASIC source through the actual mini-basic reader."""
from unittest.mock import Mock, patch
from unittest import TestCase
from test_machine_eval_buffer import _FakeMachine
from test_machine_args import machine
from support import fresh_global_env


class BasicBufferTest(TestCase):
    def setUp(self):
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
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_at_cursor(app)
        app.eval_buffer.assert_called_once_with(basic=True, source='PRINT 42')

    def test_current_line_is_used_without_selection(self):
        app = _FakeMachine('PRINT 42')
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ()
        app.tab.text.get.return_value = 'PRINT 42'
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_at_cursor(app)
        app.tab.text.get.assert_called_once_with('insert linestart', 'insert lineend')
        app.eval_buffer.assert_called_once_with(basic=True, source='PRINT 42')

    def test_basic_buffer_timing_and_syntax_errors(self):
        # Library initialization also uses the clock for BASIC TIME.
        _FakeMachine('(import (prefix (only mini-basic bbc-run) editor-basic:))').run()
        app = _FakeMachine('FOR')
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        with patch.object(machine.time, 'perf_counter', side_effect=[1.0, 1.25]):
            machine.LispMachine.eval_buffer(app, basic=True)
        out = ''.join(app.lines)
        self.assertIn('Error:', out)
        self.assertIn('0.250 s', out)
