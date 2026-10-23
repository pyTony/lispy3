"""The Machine's plain REPL skips a line that holds only a comment.

Pasting a CL Cookbook example with its ";; hello me :)" output lines gave
"Unexpected EOF while reading" for each comment line.
"""
import unittest

from test_machine_args import machine


class _FakeRepl:
    _plain_submit = machine.LispMachine._plain_submit

    def __init__(self):
        self.repl_pending = ""
        self.listener_history = []
        self.listener_hist_idx = 0


class PlainCommentTest(unittest.TestCase):

    def test_comment_only_line_is_not_evaluated(self):
        repl = _FakeRepl()
        self.assertIsNone(repl._plain_submit(";; hello me :)"))
        self.assertEqual(repl.repl_pending, "")

    def test_form_is_still_returned(self):
        repl = _FakeRepl()
        self.assertIsNone(repl._plain_submit("(let ((key :happy)"))
        self.assertEqual(repl._plain_submit("  (val t)) key)"), "(let ((key :happy)\n  (val t)) key)")
        self.assertEqual(repl._plain_submit("(+ 1 2) ; three"), "(+ 1 2) ; three")


if __name__ == '__main__':
    unittest.main()
