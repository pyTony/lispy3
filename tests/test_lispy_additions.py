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
        """A string is not a symbol: (symbol? "car") is false."""
        self.assertIs(self.ev('(string? "car")'), True)
        self.assertIs(self.ev("(symbol? 'car)"), True)
        self.assertIs(self.ev('(symbol? "car")'), False)

    def test_seq_turns_a_string_into_characters(self):
        """seq turns a string into a list of characters."""
        self.assertEqual(self.show('(seq "ab c")'), "(#\\a #\\b #\\space #\\c)")

    def test_first_and_rest_on_strings(self):
        """first, rest and last work on strings, and on an empty string give ()."""
        self.assertEqual(self.show('(first "abc")'), "#\\a")
        self.assertEqual(self.show('(rest "abc")'), '"bc"')
        self.assertEqual(self.show('(last "abc")'), "#\\c")
        self.assertEqual(self.show('(first "")'), "()")

    def test_length_counts_characters(self):
        """length counts characters, not bytes."""
        self.assertEqual(self.ev('(length "h\\u00e4n")'), 3)

    def test_escapes_and_raw_strings(self):
        """Escapes work in normal strings and are left alone in raw strings."""
        self.assertEqual(self.ev('"a\\nb\\t\\"c\\""').value, 'a\nb\t"c"')
        self.assertEqual(self.ev('"""C:\\temp "x" ; no comment"""').value, 'C:\\temp "x" ; no comment')

    def test_strings_print_back_as_they_are_read(self):
        """Strings print back exactly as they were typed, escapes included."""
        for literal in ['"plain"', '"tab\\there"', '"quote \\"x\\""', '"back\\\\slash"']:
            with self.subTest(literal):
                self.assertEqual(self.show(literal), literal)

    def test_comment_characters_inside_strings_are_text(self):
        """A ; inside a string is text, not a comment."""
        self.assertEqual(self.ev('(length "a;b")'), 3)


class MapsAndKeywordsTest(LispyTestCase):

    def test_keywords_evaluate_to_themselves(self):
        """:name evaluates to itself."""
        self.assertEqual(self.ev(":name"), ":name")

    def test_keyword_lookup(self):
        """(:name user) and get look up a map key; a missing key gives ()."""
        self.ev('(define user {:name "Tony" :age 50})')
        self.assertEqual(self.ev("(:name user)").value, "Tony")
        self.assertEqual(self.ev("(get user :age)"), 50)
        self.assertEqual(self.show("(:missing user)"), "()")

    def test_map_values_are_evaluated(self):
        """Values in a {} map literal are evaluated."""
        self.assertEqual(self.show("{:sum (+ 1 2)}"), "{:sum 3}")

    def test_keyword_lookup_on_a_non_map_is_an_error(self):
        """(:name 5) is an error, since 5 is not a map."""
        with self.assertRaises(TypeError):
            self.ev("(:name 5)")


class VectorsAndWhileTest(LispyTestCase):

    def test_bracket_vectors_evaluate_their_items(self):
        """Items in a [...] vector are evaluated."""
        self.assertEqual(self.show("[1 (+ 1 1) 3]"), "[1 2 3]")

    def test_mutable_vectors(self):
        """make-vector fills with 0, vector-set! changes an item."""
        self.ev_all("(define v (make-vector 4))", "(vector-set! v 2 7)")
        self.assertEqual(self.show("v"), "[0 0 7 0]")
        self.assertEqual(self.ev("(vector-ref v 2)"), 7)

    def test_while_loops_without_using_the_stack(self):
        """A 100000-step while loop runs without a stack overflow."""
        self.ev_all("(define i 0)", "(define total 0)",
                    "(while (< i 100000) (set! total (+ total i)) (set! i (+ i 1)))")
        self.assertEqual(self.ev("total"), sum(range(100000)))

    def test_while_with_a_false_test_never_runs(self):
        """A while whose test is false at the start never runs its body."""
        self.assertIsNone(self.ev("(while #f (car))"))


class SaveAndLoadTest(LispyTestCase):

    def test_round_trip(self):
        """save then load gives back strings, lists, maps and functions."""
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws").replace("\\", "/")
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
        """save writes nothing for a workspace with only built-ins."""
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws").replace("\\", "/")
            self.ev(f'(save "{name}")')
            with open(name + ".lisp", encoding="utf-8") as f:
                self.assertEqual(f.read(), "")


class LispFolderTest(LispyTestCase):
    """Bare names in (save "x") and (load "x") mean the lisp/ folder."""

    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        self.old_cwd, self.old_lisp_dir = os.getcwd(), lispy3.LISP_DIR
        os.chdir(self.folder.name)
        lispy3.LISP_DIR = os.path.join(self.folder.name, "lisp")

    def tearDown(self):
        os.chdir(self.old_cwd)
        lispy3.LISP_DIR = self.old_lisp_dir
        self.folder.cleanup()

    def test_save_bare_name_goes_to_lisp_folder(self):
        """(save "ws") writes lisp/ws.lisp, and (load "ws") reads it back."""
        self.ev("(define x 7)")
        self.ev('(save "ws")')
        self.assertTrue(os.path.exists(os.path.join("lisp", "ws.lisp")))
        self.assertFalse(os.path.exists("ws.lisp"))
        self.ev("(set! x 0)")
        self.ev('(load "ws")')
        self.assertEqual(self.ev("x"), 7)

    def test_file_here_wins_over_lisp_folder(self):
        """load prefers a file in the current folder over one in lisp/."""
        os.mkdir("lisp")
        with open(os.path.join("lisp", "p.lisp"), "w", encoding="utf-8") as f:
            f.write("(define where 'lisp)")
        with open("p.lisp", "w", encoding="utf-8") as f:
            f.write("(define where 'here)")
        self.ev('(load "p")')
        self.assertEqual(self.ev("where"), "here")


class CommandLineTest(LispyTestCase):
    """Options of `python lispy3.py` are not mistaken for program files."""

    def run_main(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            status = lispy3.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_version(self):
        """--version and -V print the version and exit cleanly."""
        for option in ("--version", "-V"):
            status, out, _ = self.run_main(option)
            self.assertEqual(status, 0)
            self.assertEqual(out.strip(), lispy3.version_text())
            self.assertIn(lispy3.__version__, out)

    def test_help(self):
        """--help and -h print the usage and exit cleanly."""
        for option in ("--help", "-h"):
            status, out, _ = self.run_main(option)
            self.assertEqual(status, 0)
            self.assertIn("usage:", out)

    def test_unknown_option(self):
        """An unknown option exits with status 2 and names the option."""
        status, out, err = self.run_main("--verbose")
        self.assertEqual(status, 2)
        self.assertIn("unknown option --verbose", err)
        self.assertEqual(out, "")

    def test_missing_program_fails(self):
        """A program file that does not exist exits with status 1 and names it."""
        status, _, err = self.run_main("no_such_program.lisp")
        self.assertEqual(status, 1)
        self.assertIn("no_such_program.lisp", err)


class ExampleProgramsTest(LispyTestCase):
    """Every .lisp file in the repository runs without an error."""

    def setUp(self):
        super().setUp()
        self.old_cwd = os.getcwd()
        os.chdir(REPO_DIR)                     # run from the top folder, as the README shows

    def tearDown(self):
        os.chdir(self.old_cwd)

    def run_example(self, filename):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            ok = lispy3.run_file(filename)
        self.assertTrue(ok, err.getvalue())
        return out.getvalue()

    def test_l_systems_draw(self):
        """The L-system examples and startup.lisp draw with the turtle."""
        for name in ["tree.lisp", "plant.lisp", "snowflake.lisp", "startup.lisp"]:
            with self.subTest(name):
                self.setUp()
                self.run_example(name)
                moves = [c for c in turtle_stub.calls if c[0] in ('fd', 'forward')]
                self.assertGreater(len(moves), 10)

    def test_sieve_finds_1899_primes(self):
        """sieve_lispy3.lisp finds 1899 primes."""
        self.assertIn("Primes found: 1899", self.run_example("sieve_lispy3.lisp"))

    def test_saved_workspace_loads(self):
        """my_workspace.lisp loads without an error."""
        self.run_example("my_workspace.lisp")

    def test_every_example_is_covered(self):
        """Every .lisp file in lisp/ has a test."""
        covered = {"tree.lisp", "plant.lisp", "snowflake.lisp", "sieve_lispy3.lisp",
                   "sieve-optimized.lisp", "my_workspace.lisp", "pi_digits.lisp", "lsystems.lisp"}  # pi: test_pi_digits.py
        examples = {f for f in os.listdir(lispy3.LISP_DIR) if f.endswith(".lisp")}
        self.assertEqual(examples - covered, set(), "add a test for the new example program")