"""MBASIC 5.21 compatibility of Lispy BASIC's MBASIC print style.

Runs the programs in Aaron Wohl's MBASIC (https://github.com/avwohl/mbasic)
basic/dev/tests_with_results/, whose .txt files hold the output of the real
5.21 binary. The suite is not copied here (it is GPLv3): clone it beside this
checkout, see docs/MBASIC_COMPAT.md. Without a clone the test is skipped.

EXPECTED records every program: PASS must match; anything else is an expected
failure with its reason, and fails the test if it starts to pass, so the table
stays an up-to-date backlog.
"""
import contextlib
import io
import os
import sys
import threading
import unittest
from pathlib import Path

from support import LispyTestCase, REPO_DIR, fresh_global_env, lispy3

PASS = 'pass'
SPACING = 'output differs only in spacing'
MISSING = 'statement or function not implemented'
FILES = 'CHAIN, MERGE, KILL or random files not implemented'
SEMANTICS = 'different MBASIC semantics'

EXPECTED = {
    'log10k': MISSING + ': \\', 'test_binary_conversion': MISSING + ': MKI$, CVI',
    'test_type_conversion': MISSING + ': CINT',
    'test_chain': FILES, 'test_merge': FILES, 'test_file_io': FILES, 'test_random_files': FILES,
    'test_data_read': PASS, 'test_dim_arrays': PASS, 'test_goto': PASS,
    'test_input': PASS, 'test_simple': PASS,
    'test_gosub': SPACING, 'test_tab_spc': SPACING,
    'test_def_fn': MISSING + ': DEF FN', 'test_deftypes': MISSING + ': DEFINT',
    'test_eqv_imp': MISSING + ': EQV, IMP', 'test_erase': MISSING + ': ERASE',
    'test_error_handling': MISSING + ': ON ERROR, RESUME', 'test_hex_oct': MISSING + ': HEX$, OCT$',
    'test_inkey': MISSING + ': INKEY$', 'test_logical_ops': MISSING + ': XOR',
    'test_math_functions': MISSING, 'test_mid_assignment': MISSING + ': MID$ =',
    'test_mod_intdiv': MISSING + ': \\', 'test_operator_precedence': MISSING + ': \\',
    'test_option_base': MISSING + ': OPTION BASE', 'test_peek': MISSING + ': PEEK',
    'test_print_using': MISSING + ': PRINT USING', 'test_randomize': MISSING + ': RANDOMIZE',
    'test_rounding': MISSING + ': FIX', 'test_string_functions': MISSING + ': SPACE$',
    'test_swap': MISSING + ': SWAP', 'test_tron_troff': MISSING + ': TRON, TROFF',
    'test_while_wend': PASS,
    'test_if_then_else': SEMANTICS + ': string < comparison',
    'test_on_goto_gosub': SEMANTICS + ': ON out of range falls through',
    'test_for_next': SEMANTICS + ': output differs', 'test_rnd': SEMANTICS + ': RND sequence',
}


def mbasic_tests_dir():
    """LISPY_MBASIC_DIR, else an mbasic clone or link in this checkout, else beside it."""
    root = Path(REPO_DIR)
    candidates = [Path(os.environ['LISPY_MBASIC_DIR'])] if os.environ.get('LISPY_MBASIC_DIR') else []
    candidates += [root / 'mbasic', root.parent / 'mbasic']
    for clone in candidates:
        tests = clone / 'basic' / 'dev' / 'tests_with_results'
        if tests.is_dir():
            return tests
    return None


def run_mbasic(source, timeout=10):
    """Run source in the MBASIC print style; return (output, error text)."""
    out, error = io.StringIO(), []

    def run():
        stdin = sys.stdin
        sys.stdin = io.StringIO('')
        try:
            with contextlib.redirect_stdout(out):
                lispy3.eval_exp(['bbc-run', lispy3.String(source)], lispy3.global_env)
        except BaseException as e:
            error.append(f'{type(e).__name__}: {e}')
        finally:
            sys.stdin = stdin
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        error.append('timeout')
    return out.getvalue(), ' '.join(error)


@unittest.skipIf(mbasic_tests_dir() is None, 'no MBASIC clone: see docs/MBASIC_COMPAT.md')
class MBasicCompatibilityTest(LispyTestCase):

    def test_programs_match_the_expected_table(self):
        folder = mbasic_tests_dir()
        programs = sorted(p.stem for p in folder.glob('*.bas') if p.with_suffix('.txt').exists())
        for name in programs:
            with self.subTest(program=name):
                fresh_global_env()
                lispy3.load_workspace('mini-basic')
                self.ev('(bbc-set-print-style! :mbasic)')
                source = (folder / f'{name}.bas').read_text(errors='replace').replace('\r', '')
                expected = (folder / f'{name}.txt').read_text(errors='replace').replace('\r', '')
                got, error = run_mbasic(source)
                passes = got.strip() == expected.strip()
                reason = EXPECTED.get(name)
                if reason is None:
                    self.fail(f'new program {name}: add it to EXPECTED ({"passes" if passes else error or "fails"})')
                elif reason == PASS:
                    self.assertEqual(got.strip(), expected.strip(), error)
                elif passes:
                    self.fail(f'{name} now passes: mark it PASS in EXPECTED (was: {reason})')
        self.ev('(bbc-set-print-style! :bbc)')


if __name__ == '__main__':
    unittest.main()
