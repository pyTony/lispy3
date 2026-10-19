"""Tests for turning the Listener log into runnable code (Listener "To buffer").

Run:  python -m unittest discover tests
"""
import os
import tempfile
import unittest

from support import lispy3 as L
from test_machine_args import machine

to_code = machine.listener_to_code


class ListenerToCode(unittest.TestCase):
    def test_prompts_removed_and_output_commented(self):
        """Saving the Listener as code drops the prompts and comments out the output."""
        log = ("USER> (define x 5)\n"
               ";; x defined\n"
               "USER> (* x x)\n"
               "=> 25\n"
               "USER> (car '())\n"
               "Error: car of empty list\n")
        self.assertEqual(to_code(log),
                         "(define x 5)\n"
                         ";; x defined\n"
                         "(* x x)\n"
                         ";; => 25\n"
                         ";; (car '())\n"
                         ";; Error: car of empty list\n")

    def test_plain_repl_continuation_prompts(self):
        """The plain REPL's ... (1)> continuation prompts are removed too."""
        log = ("lispy3> (define (sq n)\n"
               "... (1)>   (* n n))\n"
               "lispy3> (sq 4)\n"
               "16\n")
        self.assertEqual(to_code(log),
                         "(define (sq n)\n"
                         "  (* n n))\n"
                         "(sq 4)\n"
                         ";; 16\n")

    def test_multi_line_form_without_prompts_keeps_its_lines(self):
        """A form typed over several lines keeps its line breaks."""
        log = ("USER> (define (f)\n"
               "  (display \"hi\"))\n"
               ";; f defined\n"
               "USER> (f)\n"
               "hi\n")
        self.assertEqual(to_code(log),
                         "(define (f)\n"
                         "  (display \"hi\"))\n"
                         ";; f defined\n"
                         "(f)\n"
                         ";; hi\n")

    def test_shortened_form_is_commented_out(self):
        """A form shortened with ... is commented out, since it would not run."""
        log = "USER> (define long (list 1 2 3 4...\n=> nil\n"
        code = to_code(log)
        self.assertTrue(code.startswith(";; (define long"))
        self.assertIn(";; => nil", code)

    def test_multi_line_form_with_an_error_is_commented_out(self):
        """A multi-line form that gave an error is commented out."""
        log = ("lispy3> (display \"a\")\n"
               "a\n"
               "lispy3> (car\n"
               "... (1)>   '())\n"
               "Error: car of empty list\n"
               "lispy3> (+ 1 2)\n"
               "3\n")
        self.assertEqual(to_code(log),
                         "(display \"a\")\n"
                         ";; a\n"
                         ";; (car\n"
                         ";;   '())\n"
                         ";; Error: car of empty list\n"
                         "(+ 1 2)\n"
                         ";; 3\n")

    def test_error_after_printed_output_comments_only_the_form(self):
        """When a form printed something and then failed, all of it is commented out."""
        log = "USER> (begin (display \"hi\") (car '()))\nhi\nError: car of empty list\n"
        self.assertEqual(to_code(log),
                         ";; (begin (display \"hi\") (car '()))\n"
                         ";; hi\n"
                         ";; Error: car of empty list\n")

    def test_empty_prompts_and_blank_lines(self):
        """Empty prompts are dropped and blank lines and comments kept."""
        self.assertEqual(to_code(""), "")
        self.assertEqual(to_code("lispy3> \n\n;; note\n"), "\n;; note\n")

    def test_saved_result_runs(self):
        """The saved code runs and gives the same result as the session."""
        log = ("USER> (define total 0)\n;; total defined\n"
               "USER> (set! total (+ total 7))\n=> 7\n"
               "USER> (undefined-thing)\nError: Undefined symbol: undefined-thing\n"
               "USER> total\n=> 7\n")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "listener.lisp")
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_code(log))
            self.assertTrue(L.run_file(path))
        self.assertEqual(L.global_env["total"], 7)

if __name__ == "__main__":
    unittest.main()
