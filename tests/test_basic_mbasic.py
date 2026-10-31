"""MBASIC operators and functions in the MBASIC print style (lisp/mini-basic-mbasic.lisp)."""
import unittest

from test_mini_basic_reader import ReaderTestCase


class MBasicTestCase(ReaderTestCase):

    def run_mbasic(self, source):
        self.ev('(bbc-set-print-style! :mbasic)')
        try:
            return self.run_bbc(source)
        finally:
            self.ev('(bbc-set-print-style! :bbc)')


class OperatorsTest(MBasicTestCase):

    def test_integer_division_and_mod(self):
        self.assertEqual(self.run_mbasic('PRINT 17 \\ 5; -10 \\ 3; 10 \\ -3; 17 MOD 5; -10 MOD 3'),
                         ' 3 -3 -3  2 -1 \n')

    def test_operands_are_rounded_first(self):
        self.assertEqual(self.run_mbasic('PRINT 10.6 \\ 3; 7.5 MOD 3'), ' 3  2 \n')

    def test_precedence(self):
        self.assertEqual(self.run_mbasic('PRINT 10 + 7 MOD 3; 10 + 5 \\ 2; 10 \\ 3 MOD 2; -2 ^ 2; 2 * -3'),
                         ' 11  12  1 -4 -6 \n')

    def test_division_by_zero(self):
        with self.assertRaisesRegex(Exception, 'Division by zero'):
            self.run_mbasic('PRINT 1 \\ 0')

    def test_xor_eqv_imp(self):
        self.assertEqual(self.run_mbasic('PRINT 5 XOR 3; 5 EQV 3; 5 IMP 3; 0 IMP -1; -1 EQV 0'),
                         ' 6 -7 -5 -1  0 \n')

    def test_logical_operators_bind_loosely(self):
        self.assertEqual(self.run_mbasic('X = 10\nIF X > 5 XOR X > 20 THEN PRINT "one"\n'
                                         'PRINT NOT X = 3; 0 OR 1 XOR 1'),
                         'one\n-1  0 \n')

    def test_bbc_style_has_no_backslash(self):
        with self.assertRaisesRegex(Exception, 'unexpected character'):
            self.run_bbc('PRINT 7 \\ 2')


class FunctionsTest(MBasicTestCase):

    def test_fix_and_cint(self):
        self.assertEqual(self.run_mbasic('PRINT FIX(-2.7); CINT(-2.7); CINT(2.5); CINT(-2.5); INT(-2.7)'),
                         '-2 -3  3 -3 -3 \n')

    def test_cint_overflow(self):
        with self.assertRaisesRegex(Exception, 'Overflow'):
            self.run_mbasic('PRINT CINT(40000)')

    def test_integer_variables_round(self):
        self.assertEqual(self.run_mbasic('A% = 10.7 : B% = -5.9 : PRINT A%; B%'), ' 11 -6 \n')

    def test_hex_oct(self):
        self.assertEqual(self.run_mbasic('PRINT HEX$(255); " "; HEX$(-1); " "; OCT$(8); " "; OCT$(0)'),
                         'FF FFFF 10 0\n')

    def test_space_string_and_str(self):
        self.assertEqual(self.run_mbasic('A$ = "A" + SPACE$(3) + "B" + STR$(42) + STR$(-1)\nPRINT A$; LEN(A$)'),
                         'A   B 42-1 10 \n')

    def test_string_of_a_character_code(self):
        self.assertEqual(self.run_mbasic('PRINT STRING$(3, 42)'), '***\n')

    def test_csng_and_cdbl(self):
        self.assertEqual(self.run_mbasic('PRINT CSNG(1/3) = 1/3; CDBL(2)'), ' 0  2 \n')


class StatementsTest(MBasicTestCase):

    def test_def_fn_with_a_space(self):
        self.assertEqual(self.run_mbasic('10 DEF FN SQUARE(X) = X * X\n20 DEF FN CIRCLE(R) = 3 * R\n'
                                         '30 PRINT FN SQUARE(5); FN CIRCLE(2); FNSQUARE(3)'),
                         ' 25  6  9 \n')

    def test_randomize_repeats_the_sequence(self):
        self.assertEqual(self.run_mbasic('RANDOMIZE 42 : A = RND : RANDOMIZE 42\n'
                                         'IF A = RND AND A >= 0 AND A < 1 THEN PRINT "same"\n'
                                         'RANDOMIZE : PRINT "clock"'),
                         'same\nclock\n')

    def test_bare_rnd_is_rnd_1(self):
        self.assertEqual(self.run_mbasic('X = RND : IF X >= 0 AND X < 1 THEN PRINT "ok"'), 'ok\n')

    def test_apostrophe_comment_and_ctrl_z_end(self):
        self.assertEqual(self.run_mbasic("10 PRINT 1 ' one \\ two\n20 ' @ note\n30 END\n\x1a\x1a@@"),
                         ' 1 \n')

    def test_words_stay_names_in_bbc_style(self):
        self.assertEqual(self.run_bbc('fix = 2 : xor = 3 : PRINT fix + xor'), '         5\n')


if __name__ == '__main__':
    unittest.main()
