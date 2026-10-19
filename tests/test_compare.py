"""compare/: the same mini-basic programs give the same output in lispy3, SBCL and Clojure.

lispy3 always runs. SBCL runs when `sbcl` is on the PATH. Clojure runs when
`clojure` is on the PATH, or when CLOJURE_CP holds a Java class path with the
Clojure jars (clojure, spec.alpha and core.specs.alpha).
"""
import contextlib
import glob
import io
import os
import shutil
import subprocess
import unittest

from support import REPO_DIR, LispyTestCase, lispy3

COMPARE_DIR = os.path.join(REPO_DIR, 'compare')
PROGRAMS = sorted(glob.glob(os.path.join(COMPARE_DIR, 'programs', '*.lisp')))
BASIC_PROGRAMS = sorted(glob.glob(os.path.join(COMPARE_DIR, 'basic', '*.bas')))


def expected_output(program: str) -> str:
    with open(os.path.splitext(program)[0] + '.out', encoding='utf-8') as f:
        return f.read()


def clojure_command() -> list[str] | None:
    if shutil.which('clojure'):
        return ['clojure', '-M']
    if os.environ.get('CLOJURE_CP') and shutil.which('java'):
        return ['java', '-cp', os.environ['CLOJURE_CP'], 'clojure.main']
    return None


def run_in_lispy(expression: str) -> str:
    """What lispy3 prints for expression, with lisp/mini-basic.lisp loaded."""
    lispy3.global_env.clear()
    lispy3.global_env.update(lispy3.standard_env())
    lispy3.load_workspace('mini-basic')
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        lispy3.eval_exp(lispy3.expand(lispy3.parse(expression), True), lispy3.global_env)
    return out.getvalue()


class CompareTestCase(unittest.TestCase):

    def run_command(self, command: list[str]) -> None:
        for program in PROGRAMS:
            with self.subTest(program=os.path.basename(program)):
                result = subprocess.run(command + [program], capture_output=True, text=True, timeout=300)
                self.assertEqual(result.stdout, expected_output(program), result.stderr)


class LispyCompareTest(LispyTestCase):

    def test_there_are_programs(self):
        self.assertGreater(len(PROGRAMS), 0)

    def test_programs(self):
        for program in PROGRAMS:
            with self.subTest(program=os.path.basename(program)):
                lispy3.global_env.clear()
                lispy3.global_env.update(lispy3.standard_env())
                lispy3.load_workspace('mini-basic')
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    lispy3.load_workspace(program)
                self.assertEqual(out.getvalue(), expected_output(program))

    def test_run_lispy_takes_a_string(self):
        self.assertEqual(run_in_lispy('(run-lispy "FOR i=1 TO 2 : PRINT i : NEXT")'), '         1\n         2\n')

    def test_basic_programs(self):
        # BBC BASIC text read by the reader in lisp/mini-basic.lisp
        self.assertGreater(len(BASIC_PROGRAMS), 0)
        for program in BASIC_PROGRAMS:
            with self.subTest(program=os.path.basename(program)):
                lispy3.global_env.clear()
                lispy3.global_env.update(lispy3.standard_env())
                lispy3.load_workspace('mini-basic')
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.ev(f'(bbc-load "{program}")')
                self.assertEqual(out.getvalue(), expected_output(program))


@unittest.skipUnless(shutil.which('sbcl'), 'sbcl is not installed')
class SbclCompareTest(CompareTestCase):

    def test_programs(self):
        self.run_command(['sbcl', '--script', os.path.join(COMPARE_DIR, 'sbcl', 'run.lisp')])

    def test_basic_programs(self):
        # (run-sbcl text): the reader's forms run with compare/sbcl/mini-basic.lisp
        for program in BASIC_PROGRAMS:
            with self.subTest(program=os.path.basename(program)):
                self.assertEqual(run_in_lispy(f'(run-sbcl (slurp "{program}"))'), expected_output(program))


@unittest.skipUnless(clojure_command(), 'Clojure is not installed (or set CLOJURE_CP)')
class ClojureCompareTest(CompareTestCase):

    def test_programs(self):
        self.run_command(clojure_command() + [os.path.join(COMPARE_DIR, 'clojure', 'run.clj')])


@unittest.skipUnless(shutil.which('clojure'), 'clojure is not installed')
class RunClojureTest(unittest.TestCase):

    def test_basic_programs(self):
        # (run-clojure text): the reader's forms run with compare/clojure/mini_basic.clj
        for program in BASIC_PROGRAMS:
            with self.subTest(program=os.path.basename(program)):
                self.assertEqual(run_in_lispy(f'(run-clojure (slurp "{program}"))'), expected_output(program))


if __name__ == '__main__':
    unittest.main()
