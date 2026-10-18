"""Tests for Eval > Eval whole buffer (F6) in the Lispy Machine.

The window is not opened: eval_buffer runs on a small stand-in that records
what would be written to the Listener.

Run:  python -m unittest discover tests
"""
import unittest

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


if __name__ == "__main__":
    unittest.main()
