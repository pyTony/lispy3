"""Run editor BASIC source through the actual mini-basic reader."""
from unittest.mock import Mock, patch
import contextlib
import io
import itertools
from unittest import TestCase
from test_machine_eval_buffer import _FakeMachine as _EvalMachine
from test_machine_args import machine
from support import fresh_global_env
from lispy_support.basic_repl import BasicRepl


class _FakeMachine(_EvalMachine):
    _basic_feed = machine.LispMachine._basic_feed
    _cache_current_buffer_for_basic = machine.LispMachine._cache_current_buffer_for_basic
    _get_basic_buffer_text = machine.LispMachine._get_basic_buffer_text

    def __init__(self, content):
        super().__init__(content)
        self.basic_repl_mode = Mock()
        self.basic_repl_mode.get.return_value = True
        self._focus_listener = Mock()
        self._show_prompt = Mock()
        self.console_ready = False
        self.listener_history = []
        self.basic_repl = BasicRepl(machine.L, get_current_source=self._get_basic_buffer_text)
        # Initialize outside timing assertions, as the BASIC library itself
        # reads perf_counter for TIME during initialization.
        self.basic_repl._fresh()

    def _start(self, work, on_done=None):
        try:
            result = work()
            if on_done is not None:
                on_done(result, False)
        finally:
            self.basic_repl.close()
        return True


class BasicBufferTest(TestCase):
    def setUp(self):
        fresh_global_env()

    def tearDown(self):
        machine.L.library_system.reset()
        fresh_global_env()

    def test_whole_buffer_runs_basic_with_quotes_and_backslashes(self):
        app = _FakeMachine('FOR I%=1 TO 3\nPRINT I%\nNEXT\nPRINT "C:\\demo"')
        app.eval_buffer = lambda **kwargs: machine.LispMachine.eval_buffer(app, **kwargs)
        machine.LispMachine.eval_basic_buffer(app, backend='lispy')
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
        app.eval_buffer.assert_called_once_with(basic=True, basic_backend='python', source='PRINT 42', source_line=1)

    def test_current_line_is_used_without_selection(self):
        app = _FakeMachine('PRINT 42')
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ()
        app.tab.text.get.return_value = 'PRINT 42'
        app.tab.text.index.return_value = '5.0'
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_at_cursor(app)
        app.tab.text.get.assert_called_once_with('insert linestart', 'insert lineend')
        app.eval_buffer.assert_called_once_with(basic=True, basic_backend='python', source='PRINT 42', source_line=5)

    def test_basic_buffer_timing_and_syntax_errors(self):
        # Library initialization also uses the clock for BASIC TIME.
        _FakeMachine('(import (prefix (only mini-basic bbc-run) editor-basic:))').run()
        app = _FakeMachine('FOR')
        app.tab.text = Mock()
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        with patch.object(machine.time, 'perf_counter',
                          side_effect=itertools.chain([1.0], itertools.repeat(1.25))):
            machine.LispMachine.eval_buffer(app, basic=True)
        out = ''.join(app.lines)
        self.assertIn('Error:', out)
        self.assertIn('0.250 s', out)
        app.tab.text.tag_add.assert_called_with('syntax_error', '1.0', '1.end')

    def test_python_backend_uses_unsaved_text_and_highlights_numbered_line(self):
        app = _FakeMachine('10 PRINT 1\n100 FOR')
        app.tab.text = Mock()
        app.basic_pygame = Mock()
        app.basic_pygame.get.return_value = False
        app.settings = {'basic_directory': '/configured/mini_basic'}
        def run(source, write, **kwargs):
            self.assertEqual(source, app.tab.content)
            self.assertEqual(kwargs['package_root'], '/configured/mini_basic')
            write('Error in line 100: expected variable\n')
            return 1
        with patch.object(machine.BR, 'run_python_basic', side_effect=run):
            machine.LispMachine.eval_buffer(app, basic=True, basic_backend='python')
        app.tab.text.tag_add.assert_called_with('syntax_error', '2.0', '2.end')

    def test_lispy_selected_error_maps_to_original_buffer_line(self):
        app = _FakeMachine('; before\n; before\nFOR')
        app.tab.text = Mock()
        machine.LispMachine.eval_buffer(app, basic=True, source='FOR', source_line=3)
        app.tab.text.tag_add.assert_called_with('syntax_error', '3.0', '3.end')

    def test_cli_run_highlights_current_buffer_error(self):
        app = _FakeMachine('10 PRINT "ok"\n100 FOR')
        app.tab.text = Mock()
        app._basic_feed(['RUN'])
        self.assertIn('Error:', ''.join(app.lines))
        app.tab.text.tag_add.assert_called_with('syntax_error', '2.0', '2.end')

    def test_multiline_numbered_selection_executes_as_program(self):
        app = _FakeMachine('REM before\n10 GOTO 30\n20 PRINT "wrong"\n30 PRINT "selected"')
        machine.LispMachine.eval_buffer(app, basic=True,
            source='10 GOTO 30\n20 PRINT "wrong"\n30 PRINT "selected"', source_line=2)
        self.assertIn('selected\n', ''.join(app.lines))
        self.assertNotIn('wrong\n', ''.join(app.lines))
        self.assertNotIn('Error:', ''.join(app.lines))

    def test_error_does_not_highlight_changed_buffer(self):
        app = _FakeMachine('FOR')
        app.tab.text = Mock()
        evaluate = app._eval_with_turtle
        def edit_before_completion(callback):
            result = evaluate(callback)
            app.tab.content = 'PRINT "fixed"'
            return result
        app._eval_with_turtle = edit_before_completion
        machine.LispMachine.eval_buffer(app, basic=True)
        self.assertIn('Error:', ''.join(app.lines))
        app.tab.text.tag_add.assert_not_called()

    def test_lispy_backend_uses_selected_ansi_output(self):
        app = _FakeMachine('PRINT "terminal-only"')
        app.basic_output = Mock()
        app.basic_output.get.return_value = 'ansi'
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal), patch.object(machine.lispy_terminal, 'terminal_output_active', return_value=True):
                yield
        with patch.object(machine.lispy_terminal, 'ansi_terminal_output', output):
            machine.LispMachine.eval_buffer(app, basic=True)
        self.assertEqual(terminal.getvalue(), 'terminal-only\n')
        self.assertNotIn('terminal-only\n', app.lines)

    def test_python_backend_uses_selected_ansi_output(self):
        app = _FakeMachine('PRINT "terminal-only"')
        app.basic_output = Mock()
        app.basic_output.get.return_value = 'ansi'
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal):
                yield
        def run(source, write, **kwargs):
            write('\x1b[31mterminal-only\x1b[0m\n')
            return 0
        with patch.object(machine.BR, 'run_python_basic', side_effect=run), patch.object(machine.lispy_terminal, 'ansi_terminal_output', output):
            machine.LispMachine.eval_buffer(app, basic=True, basic_backend='python')
        self.assertIn('\x1b[31mterminal-only\x1b[0m', terminal.getvalue())
        self.assertNotIn('terminal-only', ''.join(app.lines))

    def test_output_setting_is_persisted(self):
        app = Mock()
        app.settings = {'basic_backend': 'python'}
        app.basic_pygame.get.return_value = False
        app.basic_output.get.return_value = 'ansi'
        with patch.object(machine, 'save_settings') as save:
            machine.LispMachine._save_basic_settings(app)
        self.assertEqual(save.call_args.args[0]['basic_output'], 'ansi')
        self.assertNotIn('basic_backend', save.call_args.args[0])
