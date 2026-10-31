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
                     '(bbc-program (LABEL 10) (LABEL 20) (PRINT 1) (LABEL 30) (END))')

class RunTest(ReaderTestCase):

    def test_print(self):
        self.assertEqual(self.run_bbc('PRINT "A";1;"B" : PRINT 1,2 : PRINT ;7'), 'A1B\n         1         2\n7\n')

    def test_final_comma_still_ends_the_line(self):
        # BBCSDL: only a final ; keeps the line open; MBASIC keeps it open after , too
        self.assertEqual(self.run_bbc('FOR i%=1 TO 2: PRINT i%,: NEXT\nFOR i%=1 TO 2: PRINT i%,;: NEXT'),
                         '         1\n         2\n         1         2')
        self.ev('(bbc-set-print-style! :mbasic)')
        try:
            self.assertEqual(self.run_bbc('PRINT 1,\nPRINT 2'), ' 1         2 \n')
        finally:
            self.ev('(bbc-set-print-style! :bbc)')

    def test_screen_wraps_at_80_columns_between_whole_fields(self):
        self.assertEqual(self.run_bbc('FOR i%=1 TO 9: PRINT i%,;: NEXT\nPRINT\nPRINT ;i%'),
                         ''.join(f'{i:10}' for i in range(1, 9)) + '\n         9\n10\n')

    def test_question_mark_is_print_at_statement_start(self):
        self.assertEqual(self.run_bbc('BOGOTO=23\n?BOGOTO\nA=1:?A;"x"\nIF A THEN ?"yes" ELSE ?"no"'),
                         '        23\n         1x\nyes\n')

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

    def test_angle_functions(self):
        # Wheel.bas: y1% = m1%* COS(RAD(a1%-t%)); RAD was read as an array
        source = ('m1% = 100 : a1% = 70 : t% = 10\ny1% = m1%* COS(RAD(a1%-t%))\n'
                  'PRINT y1%; " "; DEG PI; " "; DEG(ACS(0)); " "; DEG ASN 1; " "; RAD 180')
        self.assertEqual(self.run_bbc(source), '        50 180 90 90 3.14159265\n')

    def test_angle_functions_survive_turtle_radians(self):
        # Graphics bind turtle's zero-argument radians and degrees over math's
        self.ev('(define (radians) 0)')
        self.ev('(define (degrees) 0)')
        self.assertEqual(self.run_bbc('PRINT DEG PI; " "; RAD 180'), '       180 3.14159265\n')

    def test_exit_and_repeat(self):
        source = 'REPEAT : n += 1 : IF n = 4 THEN EXIT REPEAT\nUNTIL FALSE\nPRINT n'
        self.assertEqual(self.run_bbc(source), '         4\n')

    def test_case(self):
        source = 'FOR i = 1 TO 3\nCASE i OF\nWHEN 1 : PRINT "one"\nWHEN 2, 3\n  PRINT "more"\nENDCASE\nNEXT'
        self.assertEqual(self.run_bbc(source), 'one\nmore\nmore\n')

    def test_load_a_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.bas', delete=False) as f:
            f.name = f.name.replace('\\', '/')  # BBC BASIC uses forward slashes
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


class SlurpTest(LispyTestCase):

    def test_slurp_reads_a_text_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.name = f.name.replace('\\', '/')  # BBC BASIC uses forward slashes  
            f.write('two\nlines')
        try:
            self.assertEqual(self.ev(f'(slurp "{f.name}")').value, 'two\nlines')
        finally:
            os.unlink(f.name)


class FunctionTerminatorDiagnosticTest(ReaderTestCase):
    def test_numbered_recursive_function_returns_without_end_def(self):
        source = ('10 PRINT FNfact(6)\n20 END\n100 DEF FNfact(n%)\n'
                  '110 IF n%<2 THEN\n120 =1\n130 ELSE\n'
                  '140 =n%*FNfact(n%-1)\n150 ENDIF')
        self.assertEqual(self.run_bbc(source).strip(), '720')

    def test_end_def_reports_its_own_line_and_correct_function_return(self):
        with self.assertRaisesRegex(lispy3.LispyError, r'line 3: END DEF.*=expression'):
            self.expand('DEF FNf(n)\n=n+1\nEND DEF\nPRINT FNf(4)')

    def test_orphan_end_def_has_a_located_error(self):
        with self.assertRaisesRegex(lispy3.LispyError, r'line 1: END DEF.*ENDPROC'):
            self.expand('END DEF')


if __name__ == '__main__':
    unittest.main()


class RemPrefixTest(ReaderTestCase):
    def test_rem_without_space_discards_rest_of_line(self):
        self.assertEqual(self.run_bbc('10 REMM THIS IS COMMENT "unfinished\n20 PRINT "ok"'), 'ok\n')
        self.assertEqual(self.run_bbc('PRINT "REMM":REMcomment "unfinished\nPRINT "after"'), 'REMM\nafter\n')

    def test_embedded_rem_does_not_change_variable_names(self):
        self.assertEqual(self.run_bbc('PREM=7:PRINT ;PREM'), '7\n')


class KeywordPrefixNameTest(ReaderTestCase):
    """BBCSDL reads an uppercase name that starts with a keyword as that keyword."""

    def test_count_percent_is_rejected_like_bbcsdl(self):
        with self.assertRaisesRegex(lispy3.LispyError,
                                    r'line 2: COUNT% starts with the keyword COUNT.*count% or Count%'):
            self.run_bbc('PRINT 1\nCOUNT%=3')

    def test_keyword_prefixes_are_rejected(self):
        for source, word in (('TOTAL=1', 'TO'), ('PRINT ORDER', 'OR'), ('TIME%=1', 'TIME'),
                             ('X=SWAPS', 'SWAP'), ('DIM ELSEWHERE(3)', 'ELSE')):
            with self.subTest(source=source):
                with self.assertRaisesRegex(lispy3.LispyError, ' starts with the keyword ' + word + ','):
                    self.run_bbc(source)

    def test_names_bbcsdl_accepts(self):
        # A keyword marked conditional in BBCSDL's table is only a keyword when
        # no name character follows; lowercase and mixed-case names are never keywords
        self.assertEqual(self.run_bbc('COUNTER=2:TIMER=3:PIE=4:ENDX=5\nPRINT ;COUNTER+TIMER+PIE+ENDX'), '14\n')
        self.assertEqual(self.run_bbc('count%=2:Count%=3:total=4\nPRINT ;count%+Count%+total'), '9\n')

    def test_supported_keyword_runs_into_its_argument(self):
        # As in BBCSDL, DEG5 is DEG 5, like COS0
        self.assertEqual(self.run_bbc('X=DEG5:PRINT ;INT X;" ";COS0'), '286 1\n')

    def test_keywords_run_together(self):
        # Wheel.bas writes SINRAD(a) and CIRCLEFILL; TOTAL is still rejected
        self.assertEqual(self.expand('x=SINRAD(30)+COSRAD 60'),
                         '(bbc-program (LET x (+ (sin (bbc-rad 30)) (cos (bbc-rad 60)))))')

    def test_unquoted_data_words_are_not_names(self):
        self.assertEqual(self.run_bbc('READ a$\nPRINT a$\nDATA TOTAL'), 'TOTAL\n')

    def test_count_is_characters_since_the_last_new_line(self):
        self.assertEqual(self.run_bbc('PRINT "abc";:c%=COUNT:PRINT\nPRINT "é★";:d%=COUNT:PRINT\nPRINT ;c%;" ";d%;" ";COUNT'),
                         'abc\né★\n3 2 4\n')  # the last COUNT follows "3 2 "
