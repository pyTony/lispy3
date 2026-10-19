"""The BBC BASIC reader in lisp/mini-basic.lisp: text to the statement macros."""
import contextlib
import io
import os
import tempfile
import unittest

from support import LispyTestCase, lispy3


class ReaderTestCase(LispyTestCase):

    def setUp(self):
        super().setUp()
        lispy3.load_workspace('mini-basic')

    # The source goes in a """raw string""", which must not end in a quote, hence the \n

    def run_bbc(self, source: str) -> str:
        """Run BBC BASIC source with (bbc-run ...) and return what it printed."""
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-run """' + source + '\n""")')
        return out.getvalue()

    def expand(self, source: str) -> str:
        return lispy3.lisp_str(self.ev('(bbc-expand """' + source + '\n""")'))


class ExpandTest(ReaderTestCase):

    def test_fact_becomes_the_statement_macros(self):
        self.assertEqual(
            self.expand('DEF FNfact(n) IF n<2 THEN =1 ELSE =n*FNfact(n-1)\n'
                        'FOR i=1 TO 6 : PRINT "fact(";i;") = ";FNfact(i) : NEXT'),
            '(bbc-program (DEF-FN (fact n) (IF (< n 2) (FN= 1) ELSE (FN= (* n (FN fact (- n 1))))))'
            ' (FOR i 1 6 (PRINT "fact(" :semi i :semi ") = " :semi (FN fact i))))')

    def test_names_lispy3_uses_get_a_prefix(self):
        self.assertEqual(self.expand('list = 1 : t = 2 : x = list + t'),
                         '(bbc-program (LET v-list 1) (LET v-t 2) (LET x (+ v-list v-t)))')

    def test_comparisons_are_minus_one_or_zero_as_values(self):
        self.assertEqual(self.expand('a = 2 > 1'), '(bbc-program (LET a (if (> 2 1) -1 0)))')
        self.assertEqual(self.expand('IF a > 1 AND a < 3 THEN a = 0'),
                         '(bbc-program (IF (and (> a 1) (< a 3)) (LET a 0)))')

    def test_line_numbers_and_rem_are_skipped(self):
        self.assertEqual(self.expand('10 REM hello\n20 PRINT 1 : REM done\n30 END'),
                         '(bbc-program (PRINT 1) (END))')


class RunTest(ReaderTestCase):

    def test_print(self):
        self.assertEqual(self.run_bbc('PRINT "A";1;"B" : PRINT 1,2 : PRINT ;7'), 'A1B\n         1         2\n7\n')

    def test_multi_line_if_inside_a_procedure(self):
        source = ('PROCcheck(5) : PROCcheck(-1)\nEND\n'
                  'DEF PROCcheck(x)\n'
                  '  IF x < 0 THEN\n    PRINT "negative"\n    ENDPROC\n  ENDIF\n'
                  '  PRINT "positive"\nENDPROC')
        self.assertEqual(self.run_bbc(source), 'positive\nnegative\n')

    def test_single_line_if_with_several_statements(self):
        self.assertEqual(self.run_bbc('x = 3 : IF x = 3 THEN PRINT "a" : PRINT "b" ELSE PRINT "c"'), 'a\nb\n')

    def test_fn_body_over_several_lines(self):
        source = ('PRINT FNsum(4)\n'
                  'DEF FNsum(n)\n  LOCAL i, s\n  FOR i = 1 TO n : s += i : NEXT\n= s')
        self.assertEqual(self.run_bbc(source), '        10\n')

    def test_string_functions(self):
        self.assertEqual(self.run_bbc('a$ = "Hello" : a$ += "!" : PRINT LEFT$(a$, 2); MID$(a$, 3, 2); RIGHT$(a$, 1); LEN a$'),
                         'Hell!6\n')

    def test_exit_and_repeat(self):
        source = 'REPEAT : n += 1 : IF n = 4 THEN EXIT REPEAT\nUNTIL FALSE\nPRINT n'
        self.assertEqual(self.run_bbc(source), '         4\n')

    def test_case(self):
        source = 'FOR i = 1 TO 3\nCASE i OF\nWHEN 1 : PRINT "one"\nWHEN 2, 3\n  PRINT "more"\nENDCASE\nNEXT'
        self.assertEqual(self.run_bbc(source), 'one\nmore\nmore\n')

    def test_load_a_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.bas', delete=False) as f:
            f.write('PRINT "from a file"\n')
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.ev(f'(bbc-load "{f.name}")')
            self.assertEqual(out.getvalue(), 'from a file\n')
        finally:
            os.unlink(f.name)

    def test_source_may_be_an_expression(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev_all('(define prog "PRINT 6*7")', '(bbc-run prog)')
        self.assertEqual(out.getvalue(), '        42\n')


class MemoTest(ReaderTestCase):
    """A pure FN remembers its results, as in mini_basic."""

    def memoized(self, name: str) -> bool:
        return not isinstance(lispy3.global_env[name], lispy3.Procedure)

    def test_pure_fn_is_memoized(self):
        # Without the cache FNfib(60) would take far too long
        source = 'PRINT FNfib(60)\nEND\nDEF FNfib(n)\nIF n < 2 THEN = n\n= FNfib(n-1) + FNfib(n-2)'
        self.assertEqual(self.run_bbc(source), '1548008755920\n')
        self.assertTrue(self.memoized('FN-fib'))

    def test_fn_reading_a_program_variable_is_not(self):
        source = 'k = 1 : PRINT FNf(1) : k = 2 : PRINT FNf(1)\nEND\nDEF FNf(x) = x + k'
        self.assertEqual(self.run_bbc(source), '         2\n         3\n')
        self.assertFalse(self.memoized('FN-f'))

    def test_fn_that_prints_is_not(self):
        source = 'a = FNp(1) : a = FNp(1)\nEND\nDEF FNp(x)\nPRINT "hi"\n= x'
        self.assertEqual(self.run_bbc(source), 'hi\nhi\n')
        self.assertFalse(self.memoized('FN-p'))

    def test_fn_with_locals_is(self):
        source = 'PRINT FNsum(4)\nDEF FNsum(n)\n  LOCAL i, s\n  FOR i = 1 TO n : s += i : NEXT\n= s'
        self.assertEqual(self.run_bbc(source), '        10\n')
        self.assertTrue(self.memoized('FN-sum'))


class ErrorTest(ReaderTestCase):

    def assert_error(self, source: str, message: str):
        with self.assertRaises(Exception) as caught:
            self.expand(source)
        self.assertIn(message, str(caught.exception))

    def test_syntax_errors_name_the_line(self):
        self.assert_error('PRINT 1\nPRINT (2', 'line 2: expected )')
        self.assert_error('FOR i = 1 TO 3\nPRINT i', 'expected NEXT')
        self.assert_error('x = "abc', 'missing closing quote')

    def test_keywords_are_uppercase_only(self):
        self.assert_error('print 1', 'expected = after the variable')

    def test_later_steps(self):
        self.assert_error('10 GOTO 10', 'GOTO is not supported yet')
        self.assert_error('DIM a(10)', 'DIM is not supported yet')


class SlurpTest(LispyTestCase):

    def test_slurp_reads_a_text_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('two\nlines')
        try:
            self.assertEqual(self.ev(f'(slurp "{f.name}")').value, 'two\nlines')
        finally:
            os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()
