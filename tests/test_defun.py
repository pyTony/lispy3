"""Tests for the Common Lisp spelling (defun f (x) body...) and the t constant.

Run from the repository folder:

    python -m unittest discover tests
"""
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
        self.ev(FACTORIAL)
        self.assertEqual(self.ev("(factorial 5)"), 120)
        self.assertEqual(self.ev("(factorial 0)"), 1)

    def test_defun_with_several_body_expressions(self):
        self.ev("(defun two (x) (define y (* x 2)) (+ y 1))")
        self.assertEqual(self.ev("(two 5)"), 11)

    def test_defun_with_no_parameters(self):
        self.ev("(defun answer () 42)")
        self.assertEqual(self.ev("(answer)"), 42)

    def test_defun_without_parameter_list_is_an_error(self):
        with self.assertRaises(SyntaxError):
            self.ev("(defun f 42)")

    def test_t_is_true(self):
        self.assertIs(self.ev("t"), True)

    def test_defun_has_help(self):
        self.assertIn("defun", lispy3._HELP_INDEX)


class DefunNumpyTest(unittest.TestCase):

    def test_defun_in_numpy_version(self):
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
