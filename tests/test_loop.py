"""Tests for the Common Lisp loop macro and (return x).

Run from the repository folder:

    python -m unittest discover tests
"""
import contextlib
import io
import unittest

from support import LispyTestCase


class LoopTest(LispyTestCase):

    def test_do_runs_for_each_item(self):
        """Tony's first try: (loop for x in '(1 2 3) do (print x))."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(self.ev("(loop for x in '(1 2 3) do (print x))"))
        self.assertEqual(out.getvalue(), "1\n2\n3\n")

    def test_number_ranges(self):
        self.assertEqual(self.ev("(loop for i from 1 to 5 sum i)"), 15)
        self.assertEqual(self.show("(loop for i below 5 collect i)"), "(0 1 2 3 4)")
        self.assertEqual(self.show("(loop for i from 10 downto 1 by 3 collect i)"), "(10 7 4 1)")
        self.assertEqual(self.show("(loop for i from 0 below 10 by 2 collect (* i i))"), "(0 4 16 36 64)")
        self.assertEqual(self.show("(loop for i from 0 to 1 by 1/2 collect i)"), "(0 1/2 1)")
        with self.assertRaisesRegex(ValueError, "by must be positive"):
            self.ev("(loop for i from 1 to 3 by 0 collect i)")

    def test_lists_vectors_and_strings(self):
        self.assertEqual(self.show("(loop for x on '(1 2 3) collect x)"), "((1 2 3) (2 3) (3))")
        self.assertEqual(self.show("(loop for x across \"abc\" collect x)"), "(#\\a #\\b #\\c)")
        self.assertEqual(self.ev("(loop for x across [1 2 3] maximize x)"), 3)
        self.assertEqual(self.show("(loop for (a b) in '((1 2) (3 4)) collect (+ a b))"), "(3 7)")
        self.assertEqual(self.show("(loop for x in '(1 2 3) for y in '(a b c d) collect (list x y))"),
                         "((1 a) (2 b) (3 c))")
        with self.assertRaisesRegex(TypeError, "needs a list"):
            self.ev("(loop for i in 5 collect i)")

    def test_equals_then_while_and_repeat(self):
        self.assertEqual(self.show("(loop for x = 1 then (* x 2) while (< x 100) collect x)"),
                         "(1 2 4 8 16 32 64)")
        self.assertEqual(self.show("(loop repeat 3 collect 'hi)"), "(hi hi hi)")
        self.assertEqual(self.show("(loop for i from 1 until (> i 3) collect i)"), "(1 2 3)")

    def test_accumulation(self):
        self.assertEqual(self.ev("(loop for x in '(3 1 4 1 5) count (> x 2))"), 3)
        self.assertEqual(self.ev("(loop for x in '(3 1 4) minimize x)"), 1)
        self.assertEqual(self.show("(loop for x in '((1 2) (3)) append x)"), "(1 2 3)")
        self.assertEqual(self.show("(loop for x in '() maximize x)"), "()")

    def test_conditionals_and_into(self):
        self.assertEqual(self.show("(loop for x in '(1 2 3 4 5) when (odd? x) collect x)"), "(1 3 5)")
        self.assertEqual(self.show("(loop for x in '(1 2 3) unless (= x 2) collect x)"), "(1 3)")
        self.assertEqual(self.show(
            "(loop for x in '(1 2 3 4) if (even? x) collect x into evens else collect x into odds"
            " finally (return (list evens odds)))"), "((2 4) (1 3))")

    def test_with_and_finally(self):
        self.assertEqual(self.ev("(loop with s = 0 for i from 1 to 4 do (set! s (+ s i)) finally (return s))"), 10)

    def test_always_never_thereis(self):
        self.assertIs(self.ev("(loop for x in '(2 4 6) always (even? x))"), True)
        self.assertIs(self.ev("(loop for x in '(2 4 7) always (even? x))"), False)
        self.assertIs(self.ev("(loop for x in '(1 3) never (even? x))"), True)
        self.assertEqual(self.ev("(loop for x in '(1 2 3) thereis (and (> x 1) x))"), 2)

    def test_return(self):
        self.assertEqual(self.ev("(loop for i from 1 when (> (* i i) 50) return i)"), 8)
        self.assertEqual(self.ev("(loop for i from 1 do (if (> i 3) (return (* i 10))))"), 40)
        self.assertEqual(self.ev("(loop for i from 1 to 3 do (try (return i) (catch e 'caught)))"), 1)
        with self.assertRaisesRegex(SyntaxError, "not inside a loop"):
            self.ev("(return 5)")

    def test_nested_and_keywords_in_any_case(self):
        self.assertEqual(self.show("(loop for i from 1 to 2 collect (loop for j from 1 to 2 collect (* i j)))"),
                         "((1 2) (2 4))")
        self.assertEqual(self.show("(loop FOR x IN '(1 2) COLLECT x)"), "(1 2)")
        with self.assertRaisesRegex(SyntaxError, "foo is not a loop keyword"):
            self.ev("(loop for i in '(1 2) foo 3)")

    def test_named_let_called_loop_still_works(self):
        """A named let or a function called loop is not taken for the macro."""
        self.assertEqual(self.show("(let loop ((i 0) (acc '())) (if (= i 3) acc (loop (+ i 1) (cons i acc))))"),
                         "(2 1 0)")


if __name__ == '__main__':
    unittest.main()
