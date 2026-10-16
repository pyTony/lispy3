"""Tests for showing the closing brackets the reader adds by itself.

Run:  python -m unittest discover tests
"""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import turtle  # noqa: F401
except ImportError:                     # no tkinter: a stub is enough to import lispy3
    stub = types.ModuleType("turtle")
    stub.__all__ = []
    sys.modules["turtle"] = stub
import lispy3 as L


class AutoClose(unittest.TestCase):
    def test_closers_in_order(self):
        self.assertEqual(L.missing_closers("(+ 1 [2 {:a (* 3 4"), ")}])")
        self.assertEqual(L.auto_close("(+ 1 (* 2 3"), ("(+ 1 (* 2 3))", "))"))

    def test_balanced_text_is_unchanged(self):
        self.assertEqual(L.auto_close("(+ 1 2) [3]"), ("(+ 1 2) [3]", ""))

    def test_brackets_in_strings_chars_and_comments_do_not_count(self):
        self.assertEqual(L.missing_closers('(display "(" #\\( """[""") ; ('), "")
        self.assertEqual(L.missing_closers('(display ")"'), ")")

    def test_closers_go_before_a_trailing_comment(self):
        text = "(define (sq x)\n  (* x x) ; square\n"
        self.assertEqual(L.auto_close(text),
                         ("(define (sq x)\n  (* x x)) ; square\n", ")"))

    def test_closed_text_reads_the_same(self):
        text = "(begin (define x [1 2 (+ 3 4"
        closed, _ = L.auto_close(text)
        self.assertEqual(L.parse(closed), L.parse(text))


if __name__ == "__main__":
    unittest.main()
