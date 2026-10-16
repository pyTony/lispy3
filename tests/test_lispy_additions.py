"""Tests for Lispy's own additions to Norvig's lis.py.

Strings and characters, maps and keywords, vectors, while, save/load, and
the example programs in the repository. Run from the repository folder:

    python -m unittest discover tests
"""
import contextlib
import io
import os
import tempfile

import turtle_stub
from support import LispyTestCase, REPO_DIR, lispy3


class StringsAndCharactersTest(LispyTestCase):

    def test_strings_are_not_symbols(self):
        self.assertIs(self.ev('(string? "car")'), True)
        self.assertIs(self.ev("(symbol? 'car)"), True)
        self.assertIs(self.ev('(symbol? "car")'), False)

    def test_seq_turns_a_string_into_characters(self):
        self.assertEqual(self.show('(seq "ab c")'), "(#\\a #\\b #\\space #\\c)")

    def test_first_and_rest_on_strings(self):
        self.assertEqual(self.show('(first "abc")'), "#\\a")
        self.assertEqual(self.show('(rest "abc")'), '"bc"')
        self.assertEqual(self.show('(last "abc")'), "#\\c")
        self.assertEqual(self.show('(first "")'), "()")

    def test_length_counts_characters(self):
        self.assertEqual(self.ev('(length "h\\u00e4n")'), 3)

    def test_escapes_and_raw_strings(self):
        self.assertEqual(self.ev('"a\\nb\\t\\"c\\""').value, 'a\nb\t"c"')
        self.assertEqual(self.ev('"""C:\\temp "x" ; no comment"""').value, 'C:\\temp "x" ; no comment')

    def test_strings_print_back_as_they_are_read(self):
        for literal in ['"plain"', '"tab\\there"', '"quote \\"x\\""', '"back\\\\slash"']:
            with self.subTest(literal):
                self.assertEqual(self.show(literal), literal)

    def test_comment_characters_inside_strings_are_text(self):
        self.assertEqual(self.ev('(length "a;b")'), 3)


class MapsAndKeywordsTest(LispyTestCase):

    def test_keywords_evaluate_to_themselves(self):
        self.assertEqual(self.ev(":name"), ":name")

    def test_keyword_lookup(self):
        self.ev('(define user {:name "Tony" :age 50})')
        self.assertEqual(self.ev("(:name user)").value, "Tony")
        self.assertEqual(self.ev("(get user :age)"), 50)
        self.assertEqual(self.show("(:missing user)"), "()")

    def test_map_values_are_evaluated(self):
        self.assertEqual(self.show("{:sum (+ 1 2)}"), "{:sum 3}")

    def test_keyword_lookup_on_a_non_map_is_an_error(self):
        with self.assertRaises(TypeError):
            self.ev("(:name 5)")


class VectorsAndWhileTest(LispyTestCase):

    def test_bracket_vectors_evaluate_their_items(self):
        self.assertEqual(self.show("[1 (+ 1 1) 3]"), "(1 2 3)")

    def test_mutable_vectors(self):
        self.ev_all("(define v (make-vector 4))", "(vector-set! v 2 7)")
        self.assertEqual(self.show("v"), "(0 0 7 0)")
        self.assertEqual(self.ev("(vector-ref v 2)"), 7)

    def test_while_loops_without_using_the_stack(self):
        self.ev_all("(define i 0)", "(define total 0)",
                    "(while (< i 100000) (set! total (+ total i)) (set! i (+ i 1)))")
        self.assertEqual(self.ev("total"), sum(range(100000)))

    def test_while_with_a_false_test_never_runs(self):
        self.assertIsNone(self.ev("(while #f (car))"))


class SaveAndLoadTest(LispyTestCase):

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws")
            self.ev_all('(define greeting "hi \\"you\\"")', "(define nums '(1 2 3))",
                        "(define user {:name \"Tony\"})", "(define (twice x) (* 2 x))",
                        "(define car (lambda [x] 'mine))")   # a user function under a built-in name
            self.assertIn("saved", self.ev(f'(save "{name}")'))
            lispy3.global_env.clear()
            lispy3.global_env.update(lispy3.standard_env())
            self.assertIn("twice", self.ev(f'(load "{name}")'))
        self.assertEqual(self.ev("greeting").value, 'hi "you"')
        self.assertEqual(self.show("nums"), "(1 2 3)")
        self.assertEqual(self.ev("(:name user)").value, "Tony")
        self.assertEqual(self.ev("(twice 21)"), 42)
        self.assertEqual(self.ev("(car '(1))"), 'mine')

    def test_built_ins_are_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws")
            self.ev(f'(save "{name}")')
            with open(name + ".lisp", encoding="utf-8") as f:
                self.assertEqual(f.read(), "")


class ExampleProgramsTest(LispyTestCase):
    """Every .lisp file in the repository runs without an error."""

    def setUp(self):
        super().setUp()
        self.old_cwd = os.getcwd()
        os.chdir(REPO_DIR)                     # the examples load "lsystems" by its plain name

    def tearDown(self):
        os.chdir(self.old_cwd)

    def run_example(self, filename):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            ok = lispy3.run_file(filename)
        self.assertTrue(ok, err.getvalue())
        return out.getvalue()

    def test_l_systems_draw(self):
        for name in ["tree.lisp", "plant.lisp", "snowflake.lisp", "demo.lisp"]:
            with self.subTest(name):
                self.setUp()
                self.run_example(name)
                moves = [c for c in turtle_stub.calls if c[0] in ('fd', 'forward')]
                self.assertGreater(len(moves), 10)

    def test_sieve_finds_1899_primes(self):
        self.assertIn("Primes found: 1899", self.run_example("sieve_lispy3.lisp"))

    def test_saved_workspace_loads(self):
        self.run_example("my_workspace.lisp")

    def test_every_example_is_covered(self):
        covered = {"tree.lisp", "plant.lisp", "snowflake.lisp", "demo.lisp", "sieve_lispy3.lisp",
                   "my_workspace.lisp", "pi_digits.lisp", "lsystems.lisp"}  # pi: test_pi_digits.py
        examples = {f for f in os.listdir(REPO_DIR) if f.endswith(".lisp")}
        self.assertEqual(examples - covered, set(), "add a test for the new example program")
