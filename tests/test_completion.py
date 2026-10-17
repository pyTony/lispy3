"""Tests for Tab completion in the REPL and the editor's plain lispy3 REPL option.

Run:  python -m unittest discover tests
"""
import os
import tempfile
import unittest

from support import LispyTestCase, lispy3
from test_machine_args import machine


class CompleteNamesTest(LispyTestCase):

    def test_built_ins_and_special_forms(self):
        self.assertEqual(lispy3.complete_names("defi"), ["define", "define-macro"])
        self.assertIn("lambda", lispy3.complete_names("lam"))
        self.assertIn("sqrt", lispy3.complete_names("sq"))

    def test_own_definitions(self):
        self.ev("(define my-square (lambda [x] (* x x)))")
        self.assertEqual(lispy3.complete_names("my-sq"), ["my-square"])

    def test_keywords_of_global_maps(self):
        self.ev('(define user {:name "Tony" :status "Trusty"})')
        self.assertEqual(lispy3.complete_names(":"), [":name", ":status"])

    def test_no_match(self):
        self.assertEqual(lispy3.complete_names("no-such-name-"), [])


class ReplStrTest(LispyTestCase):

    def test_short_result_stays_on_one_line(self):
        self.assertEqual(lispy3.repl_str(self.ev("[1 2 3]"), 40), lispy3.lisp_str(self.ev("[1 2 3]")))

    def test_long_function_is_indented(self):
        self.ev("(define f (lambda [x] (begin (define a 1) (define b 2) (while (< a x) (set! a (+ a 1))) a)))")
        lines = lispy3.repl_str(self.ev("f"), 40).splitlines()
        self.assertEqual(lines[:3], ["(define f", "  (lambda [x]", "    (begin"])
        self.assertEqual(lines[3], "      (define a 1)")


class MachineOptionsTest(unittest.TestCase):

    def test_repl_flag_anywhere(self):
        self.assertEqual(machine.parse_args(["a.lisp", "--repl", "b.lisp"]),
                         (True, ["a.lisp", "b.lisp"]))
        self.assertEqual(machine.parse_args(["a.lisp"]), (False, ["a.lisp"]))

    def test_common_prefix(self):
        self.assertEqual(machine.common_prefix(["define", "define-macro"]), "define")

    def test_name_being_typed(self):
        self.assertEqual(machine.SYMBOL_TAIL.search("(:na").group(0), ":na")
        self.assertEqual(machine.SYMBOL_TAIL.search("(string->sy").group(0), "string->sy")

    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "settings.json")
            self.assertEqual(machine.load_settings(path), {})
            machine.save_settings({"plain_repl": True}, path)
            self.assertEqual(machine.load_settings(path), {"plain_repl": True})
            with open(path, "w") as f:
                f.write("not json")
            self.assertEqual(machine.load_settings(path), {})


if __name__ == "__main__":
    unittest.main()
