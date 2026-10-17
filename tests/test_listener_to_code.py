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
                         "(car '())\n"
                         ";; Error: car of empty list\n")

    def test_plain_repl_continuation_prompts(self):
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
        log = "USER> (define long (list 1 2 3 4...\n=> nil\n"
        code = to_code(log)
        self.assertTrue(code.startswith(";; (define long"))
        self.assertIn(";; => nil", code)

    def test_empty_prompts_and_blank_lines(self):
        self.assertEqual(to_code(""), "")
        self.assertEqual(to_code("lispy3> \n\n;; note\n"), "\n;; note\n")

    def test_saved_result_runs(self):
        log = ("USER> (define total 0)\n;; total defined\n"
               "USER> (set! total (+ total 7))\n=> 7\n"
               "Error: something printed\n"
               "USER> total\n=> 7\n")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "listener.lisp")
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_code(log))
            self.assertTrue(L.run_file(path))
        self.assertEqual(L.global_env["total"], 7)

if __name__ == "__main__":
    unittest.main()
