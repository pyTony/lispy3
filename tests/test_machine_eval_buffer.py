"""Tests for Eval > Eval whole buffer (F6) in the Lispy Machine.

The window is not opened: eval_buffer runs on a small stand-in that records
what would be written to the Listener.

Run:  python -m unittest discover tests
"""
import unittest
from unittest.mock import patch, Mock

import turtle_stub
from support import fresh_global_env
from test_machine_args import machine


class _Tab:
    name = "test.lisp"

    def __init__(self, content):
        self.content = content

    def get_content(self):
        return self.content


class _FakeMachine:
    """Just enough of LispMachine for eval_buffer."""
    _parse_top_level_forms = machine.LispMachine._parse_top_level_forms
    _defined_name = staticmethod(machine.LispMachine._defined_name)
    _eval_with_turtle = machine.LispMachine._eval_with_turtle
    _eval_forms = machine.LispMachine._eval_forms
    _echo_form = machine.LispMachine._echo_form
    _report_form = machine.LispMachine._report_form
    _report_form_error = machine.LispMachine._report_form_error
    _ui_post = machine.LispMachine._ui_post

    def _busy(self):
        return False

    def _start(self, work, on_done=None):
        """Run the work here and now, as the Lisp thread would."""
        work()
        return True

    def _ui(self, fn, *args):
        return fn(*args)

    def __init__(self, content):
        self.tab = _Tab(content)
        self.lines = []

    def current_tab(self):
        return self.tab

    def listener_write(self, text, tag=None):
        self.lines.append(text)

    def set_inspector(self, text):
        pass

    def inspect_symbol(self, name):
        pass

    def _inspector_cols(self):
        return 60

    def _fmt_result(self, val, flat):
        return flat

    def run(self):
        machine.LispMachine.eval_buffer(self)
        return "".join(self.lines)


class EvalBufferTest(unittest.TestCase):

    def setUp(self):
        fresh_global_env()

    def test_optional_timing_reports_whole_run(self):
        app = _FakeMachine('(define timed-value 4)\n(+ timed-value 2)')
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        with patch.object(machine.time, 'perf_counter', side_effect=[10.0, 10.125]):
            out = app.run()
        self.assertIn('6', out)
        self.assertIn(';; Buffer elapsed time: 0.125 s', out)

    def test_timing_is_off_by_default(self):
        self.assertNotIn('Buffer elapsed time:', _FakeMachine('(+ 1 2)').run())

    def test_timing_also_wraps_terminal_runs(self):
        app = _FakeMachine('(+ 1 2)')
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        app._eval_forms_in_terminal = Mock()
        with patch.object(machine.time, 'perf_counter', side_effect=[1.0, 1.5]):
            machine.LispMachine.eval_buffer(app, terminal=True)
        app._eval_forms_in_terminal.assert_called_once()
        self.assertIn(';; Buffer elapsed time: 0.500 s', ''.join(app.lines))

    def test_timing_reports_aborted_run(self):
        app = _FakeMachine('(unknown-timed-procedure)')
        app.time_buffer_runs = Mock()
        app.time_buffer_runs.get.return_value = True
        with patch.object(machine.time, 'perf_counter', side_effect=[1.0, 1.25]):
            out = app.run()
        self.assertIn('aborted', out)
        self.assertIn(';; Buffer elapsed time: 0.250 s', out)

    def test_forms_are_echoed_laid_out_by_default(self):
        out = _FakeMachine('(defun greet (name) (format t "hello ~a" name) (format t "!"))\n'
                           '(greet "me")\n').run()
        self.assertIn('USER> (defun greet (name)\n        (format t "hello ~a" name)\n', out)
        self.assertNotIn('...', out)
        self.assertIn('hello me!', out)

    def test_one_line_echo_is_still_available(self):
        app = _FakeMachine('(define (f x) (* x x))\n(f 4)')
        app.buffer_echo = Mock()
        app.buffer_echo.get.return_value = 'line'
        out = app.run()
        self.assertIn('USER> (define (f x) (* x x))\n', out)

    def test_silent_run_shows_only_output_values_and_errors(self):
        app = _FakeMachine('(define (f x) (display x) (newline))\n(f 7)\n(+ 1 2)\n(no-such-function 5)')
        app.buffer_echo = Mock()
        app.buffer_echo.get.return_value = 'off'
        out = app.run()
        self.assertNotIn('USER>', out)
        self.assertNotIn('evaluating', out)
        self.assertNotIn(';; f defined', out)
        self.assertNotIn(';; ok', out)
        self.assertIn('3', out)
        self.assertIn('Error', out)

    def test_defun_in_a_buffer(self):
        """F6 runs a buffer with defun and reports the function as defined."""
        out = _FakeMachine("(defun factorial (n) (cond ((= n 0) 1) (t (* n (factorial (- n 1))))))\n"
                           "(factorial 5)\n").run()
        self.assertNotIn("Error", out)
        self.assertIn(";; factorial defined", out)
        self.assertIn("120", out)

    def test_macro_defined_earlier_in_the_buffer(self):
        """F6 expands a macro defined earlier in the same buffer."""
        out = _FakeMachine("(define-macro (unless c body) `(if ,c #f ,body))\n"
                           "(unless #f 42)\n").run()
        self.assertNotIn("Error", out)
        self.assertIn("42", out)

    def test_runs_again_after_the_turtle_window_was_closed(self):
        """Closing the window leaves turtle's running flag off; F6 turns it back on."""
        turtle_stub.TurtleScreen._RUNNING = False
        out = _FakeMachine("(fd 10)\n").run()
        self.assertNotIn("Error", out)
        self.assertTrue(turtle_stub.TurtleScreen._RUNNING)

    def test_a_closed_window_is_named_in_the_error(self):
        """A turtle Terminator, which has no message, is reported in words."""
        import lispy3

        def closed(*args):
            raise turtle_stub.Terminator()
        lispy3.global_env['closed'] = closed
        out = _FakeMachine("(closed)\n").run()
        self.assertIn("Error: Turtle window was closed", out)


if __name__ == "__main__":
    unittest.main()
