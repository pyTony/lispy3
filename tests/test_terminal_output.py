"""Program/GUI output routing and silent loader status."""
import contextlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from support import LispyTestCase, lispy3
from test_machine_args import machine
from test_machine_eval_buffer import _FakeMachine


class TerminalRoutingTest(LispyTestCase):
    def test_with_ansi_terminal_keeps_workspace_state_and_return_value(self):
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal):
                yield
        with patch('lispy_terminal.ansi_terminal_output', output):
            self.ev('(define terminal-value 1)')
            result = self.ev('(with-ansi-terminal (set! terminal-value 2) (display "terminal") (+ terminal-value 3))')
        self.assertEqual(result, 5)
        self.assertEqual(self.ev('terminal-value'), 2)
        self.assertEqual(terminal.getvalue(), 'terminal\n')

    def test_terminal_errors_restore_output_and_remain_visible(self):
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal):
                yield
        listener = io.StringIO()
        with contextlib.redirect_stdout(listener):
            with patch('lispy_terminal.ansi_terminal_output', output):
                with self.assertRaisesRegex(lispy3.LispyError, 'expected error'):
                    self.ev('(with-ansi-terminal (error "expected error"))')
            self.ev('(display "listener")')
        self.assertEqual(listener.getvalue(), 'listener\n')

    def test_silent_load_has_no_status_but_keeps_explicit_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'library.lisp'
            path.write_text('(define silent-value 42) (display "explicit")', encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = self.ev('(load "'+path.as_posix()+'" :silent)')
            self.assertIsNone(result)
            self.assertEqual(self.ev('silent-value'), 42)
            self.assertEqual(out.getvalue(), 'explicit\n')
            self.assertIn('Workspace loaded', self.ev('(load "'+path.as_posix()+'")'))

    def test_silent_load_does_not_hide_errors(self):
        with self.assertRaises(FileNotFoundError):
            self.ev('(load "missing-silent-library-file" :silent)')

    def test_gui_can_evaluate_unsaved_buffer_in_terminal(self):
        app = _FakeMachine('(display "colour")\n(define gui-terminal-value 9)')
        app.basic_output = Mock()
        app._save_basic_settings = Mock()
        app.eval_buffer = lambda **kwargs: machine.LispMachine.eval_buffer(app, **kwargs)
        app._eval_forms_in_terminal = lambda forms: machine.LispMachine._eval_forms_in_terminal(app, forms)
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal), patch('lispy_terminal.terminal_output_active', return_value=True):
                yield
        with patch('lispy_terminal.ansi_terminal_output', output):
            machine.LispMachine.eval_buffer_in_terminal(app)
        self.assertEqual(terminal.getvalue(), 'colour\n')
        self.assertEqual(self.ev('gui-terminal-value'), 9)
        self.assertNotIn('colour\n', app.lines)

    def test_gui_silent_load_builds_a_quoted_path(self):
        calls = []
        app = type('SilentLoader', (), {'_busy': lambda self: False,
               '_run_silent': lambda self, code: calls.append(code)})()
        with patch.object(machine.filedialog, 'askopenfilename', return_value='C:/library path/demo.lisp'):
            machine.LispMachine.load_library_silently(app)
        self.assertEqual(calls, ['(load "C:/library path/demo.lisp" :silent)'])
