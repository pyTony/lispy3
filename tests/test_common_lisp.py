"""Tests for Common Lisp spellings: defun, t, float, &rest, CL format and nth, and the aliases.

Run from the repository folder:

    python -m unittest discover tests
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

from support import LispyTestCase, REPO_DIR, TESTS_DIR, lispy3

FACTORIAL = """(defun factorial (n)
  (cond ((= n 0) 1)
        (t (* n (factorial (- n 1))))))"""


class DefunTest(LispyTestCase):

    def test_defun_factorial_with_t_clause(self):
        """Tony's CL factorial with defun and a (t ...) cond clause works."""
        self.ev(FACTORIAL)
        self.assertEqual(self.ev("(factorial 5)"), 120)
        self.assertEqual(self.ev("(factorial 0)"), 1)

    def test_defun_with_several_body_expressions(self):
        """A defun body with several expressions runs them all and returns the last."""
        self.ev("(defun two (x) (define y (* x 2)) (+ y 1))")
        self.assertEqual(self.ev("(two 5)"), 11)

    def test_defun_with_no_parameters(self):
        """(defun answer () 42) defines a function of no arguments."""
        self.ev("(defun answer () 42)")
        self.assertEqual(self.ev("(answer)"), 42)

    def test_defun_without_parameter_list_is_an_error(self):
        """(defun f 42) with no parameter list is a SyntaxError."""
        with self.assertRaises(SyntaxError):
            self.ev("(defun f 42)")

    def test_t_is_true(self):
        """t evaluates to true."""
        self.assertIs(self.ev("t"), True)

    def test_float(self):
        """(float x) turns the exact 1/3 into a decimal, and has help."""
        self.assertEqual(self.ev("(/ 1 3)"), lispy3.Fraction(1, 3))
        self.assertEqual(self.ev("(float (/ 1 3))"), 1 / 3)
        self.assertIsInstance(self.ev("(float 2)"), float)
        self.assertIn("float", lispy3._HELP_INDEX)

    def test_rest_and_body_parameters(self):
        """&rest collects the remaining arguments into a list, empty when there are none."""
        self.ev("(defun rst (a &rest more) more)")
        self.assertEqual(self.ev("(rst 1 2 3)"), [2, 3])
        self.assertEqual(self.ev("(rst 1)"), [])
        self.assertEqual(self.ev("((lambda (&rest xs) xs) 1 2)"), [1, 2])

    def test_defmacro_with_body(self):
        """defmacro with &body works like define-macro."""
        self.ev("(defmacro my-unless (c &body body) `(if ,c nil (progn ,@body)))")
        self.assertEqual(self.ev("(my-unless nil 1 2)"), 2)
        self.assertEqual(self.ev("(my-unless t 1 2)"), [])

    def test_nth_in_both_orders(self):
        """nth takes (nth i lst) or (nth lst i), and errors on a non-list."""
        self.assertEqual(self.ev("(nth 1 '(a b c))"), "b")
        self.assertEqual(self.ev("(nth '(a b c) 1)"), "b")
        self.assertEqual(self.ev('(nth 1 "abc")'), lispy3.Char("b"))
        with self.assertRaises(TypeError):
            self.ev("(nth 5 7)")

    def test_format_destinations(self):
        """(format nil ...) returns text, (format t ...) prints it, {} style still works."""
        self.assertEqual(self.ev('(format nil "~a and ~a" 1 2)'), lispy3.String("1 and 2"))
        self.assertEqual(self.ev('(format nil "~d" 42)'), lispy3.String("42"))
        self.assertEqual(self.ev('(format "{} x" 1)'), lispy3.String("1 x"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(self.ev('(format t "x=~a~%" 5)'))
        self.assertEqual(out.getvalue(), "x=5\n")

    def test_definition_spellings(self):
        """defvar, defparameter, defconstant, setq and progn work."""
        self.ev("(defvar *v* 10)")
        self.ev('(defparameter *p* 20 "a doc string")')
        self.ev("(defconstant +c+ 3)")
        self.assertEqual(self.ev("(+ *v* *p* +c+)"), 33)
        self.ev("(setq *v* 11)")
        self.assertEqual(self.ev("*v*"), 11)
        self.assertEqual(self.ev("(progn 1 2 3)"), 3)

    def test_aliases(self):
        """CL names like null, evenp, mapcar and rem give the built-in's answer."""
        cases = {"(null '())": True, "(listp '(1))": True, "(consp '())": False,
                 "(evenp 4)": True, "(oddp 4)": False, "(zerop 0)": True, "(plusp 3)": True,
                 "(minusp -3)": True, "(numberp 1)": True, "(integerp 1)": True,
                 '(stringp "a")': True, "(symbolp 'a)": True, "(eq 'a 'a)": True,
                 "(equal '(1 2) '(1 2))": True, "(rem -17 5)": -2,
                 "(mapcar (lambda (x) (* 2 x)) '(1 2 3))": [2, 4, 6],
                 "(remove-if-not even? '(1 2 3 4))": [2, 4], "(aref (vector 1 2 3) 1)": 2}
        for code, expected in cases.items():
            with self.subTest(code=code):
                self.assertEqual(self.ev(code), expected)
        self.assertEqual(self.ev('(string-upcase "abc")'), lispy3.String("ABC"))
        self.assertIn("mapcar", lispy3._HELP_INDEX)

    def test_defun_has_help(self):
        """(help 'defun) has an entry."""
        self.assertIn("defun", lispy3._HELP_INDEX)


class DefunNumpyTest(unittest.TestCase):

    def test_defun_in_numpy_version(self):
        """defun and t work in lispy3-numpy.py run as a script."""
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("NumPy is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "fact.lisp")
            with open(script, "w") as f:
                f.write(FACTORIAL + "\n(display (factorial 10))\n")
            code = ("import sys; sys.path[:0] = [%r, %r]; import turtle_stub; "
                    "sys.modules['turtle'] = turtle_stub; import runpy; "
                    "sys.argv = ['lispy3-numpy.py', %r]; "
                    "runpy.run_path(%r, run_name='__main__')"
                    % (TESTS_DIR, REPO_DIR, script, os.path.join(REPO_DIR, "lispy3-numpy.py")))
            result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                    text=True, timeout=60)
        self.assertIn("3628800", result.stdout, result.stderr)


if __name__ == "__main__":
    unittest.main()
