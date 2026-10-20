"""Tests for the extras lispy3-numpy.py adds: make-num-vector and their help.

lispy3-numpy.py changes lispy3 as it loads, so it runs in its own Python.

Run:  python -m unittest discover tests
"""
import os
import re
import subprocess
import sys
import unittest

from support import REPO_DIR, TESTS_DIR


def run_numpy_repl(*lines: str) -> list[str]:
    """Type `lines` at the lispy3-numpy.py prompt; return what each one printed."""
    code = ("import sys; sys.path[:0] = [%r, %r]; import turtle_stub; "
            "sys.modules['turtle'] = turtle_stub; import runpy; "
            "runpy.run_path(%r, run_name='__main__')"
            % (TESTS_DIR, REPO_DIR, os.path.join(REPO_DIR, "lispy3-numpy.py")))
    result = subprocess.run([sys.executable, "-c", code], input="\n".join(lines) + "\n",
                            capture_output=True, text=True, timeout=60)
    out = re.sub(r"\x1b\[[0-9;]*m|[\x01\x02]", "", result.stdout)   # colours and readline markers
    return [part.splitlines()[0] if part.strip() else "" for part in out.split("lispy3> ")[1:-1]]


class MakeNumVector(unittest.TestCase):
    def test_from_vector_and_list(self):
        """make-num-vector takes the items of a vector or a quoted list as well as a count."""
        made = run_numpy_repl("(make-num-vector [1 2 3])", "(make-num-vector '(4 5))",
                              "(sum (make-num-vector [1 2 3]))")
        self.assertEqual(made[0].replace("#a", ""), "(1 2 3)")
        self.assertEqual(made[1].replace("#a", ""), "(4 5)")
        self.assertEqual(made[2], "6")

    def test_count_and_fill_still_work(self):
        """(make-num-vector n fill) still makes n copies of fill."""
        self.assertEqual(run_numpy_repl("(make-num-vector 3 7)")[0].replace("#a", ""), "(7 7 7)")


class ExtrasHelp(unittest.TestCase):
    def test_help_explains_the_extras(self):
        """(help make-num-vector) and (help 'sum) explain them instead of saying there is no help."""
        shown = run_numpy_repl("(help make-num-vector)", "(help 'vector-fill!)", "(help 'sum)")
        self.assertTrue(shown[0].startswith("(make-num-vector n fill)"), shown[0])
        self.assertTrue(shown[1].startswith("(vector-fill! v x"), shown[1])
        self.assertTrue(shown[2].startswith("(sum v)"), shown[2])


if __name__ == "__main__":
    unittest.main()
