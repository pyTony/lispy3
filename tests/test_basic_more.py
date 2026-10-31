"""BASIC statements BBC BASIC and MBASIC share (lisp/mini-basic-more.lisp)."""
import io
import sys
import unittest
from unittest import mock

from support import lispy3
from test_mini_basic_reader import ReaderTestCase


class SwapAndMidTest(ReaderTestCase):

    def test_swap_numbers_and_strings(self):
        self.assertEqual(self.run_bbc('a=1:b=2:SWAP a,b:PRINT a;b\n'
                                      'a$="x":b$="y":SWAP a$,b$:PRINT a$;b$'), '         21\nyx\n')

    def test_swap_array_elements(self):
        self.assertEqual(self.run_bbc('DIM n(3):n(1)=5:n(3)=7:SWAP n(1),n(3):PRINT n(1);n(3)'),
                         '         75\n')

    def test_swap_needs_matching_types(self):
        with self.assertRaisesRegex(Exception, 'two strings or two numbers'):
            self.run_bbc('a=1:b$="x":SWAP a,b$')

    def test_mid_assignment_keeps_the_length(self):
        self.assertEqual(self.run_bbc(
            'a$="hello":MID$(a$,2,2)="XYZ":PRINT a$\n'
            'MID$(a$,4)="0123":PRINT a$\n'
            'DIM s$(1):s$(1)="abc":MID$(s$(1),3)="Z":PRINT s$(1)'),
            'hXYlo\nhXY01\nabZ\n')


class OperatorsTest(ReaderTestCase):

    def test_multiply_and_divide_assignment(self):
        self.assertEqual(self.run_bbc('a=3:a*=4:a/=8:PRINT a\nDIM b(1):b(1)=2:b(1)*=5:PRINT b(1)'),
                         '       1.5\n        10\n')

    def test_string_comparison(self):
        self.assertEqual(self.run_bbc(
            'IF "APPLE"<"BANANA" THEN PRINT "less"\n'
            'a$="b":PRINT a$>"a";" ";a$<="a";" ";a$>="b";" ";"A"<"a"'),
            'less\n        -1 0 -1 -1\n')


class FunctionsTest(ReaderTestCase):

    def test_string_repeat(self):
        self.assertEqual(self.run_bbc('PRINT STRING$(3,"ab");"[";STRING$(0,"x");"]"'),
                         'ababab[]\n')

    def test_left_and_right_with_one_argument(self):
        self.assertEqual(self.run_bbc('PRINT LEFT$("abc");"|";RIGHT$("abc");"|";RIGHT$("abc",5)'),
                         'ab|c|abc\n')

    def test_eval(self):
        self.assertEqual(self.run_bbc('x=3:PRINT EVAL("1+2*x")\nb$="ab":a$=EVAL("b$")+"c":PRINT a$'),
                         '         7\nabc\n')

    def test_pos_and_vpos(self):
        self.assertEqual(self.run_bbc('PRINT "a":PRINT "bc";:p=POS:v=VPOS:PRINT\nPRINT p;v'),
                         'a\nbc\n         21\n')


class StatementsTest(ReaderTestCase):

    def test_clear_forgets_variables(self):
        self.assertEqual(self.run_bbc('a=5:b$="x":CLEAR:PRINT a;"[";b$;"]"'), '         0[]\n')

    def test_quit_stops_like_end(self):
        self.assertEqual(self.run_bbc('PRINT 1:QUIT:PRINT 2'), '         1\n')


class KeysTest(ReaderTestCase):

    def run_typed(self, source, typed):
        with mock.patch.object(sys, 'stdin', io.StringIO(typed)):
            return self.run_bbc(source)

    def test_get_reads_typed_characters_then_return(self):
        self.assertEqual(self.run_typed('k=GET:k$=GET$:PRINT k;" ";k$;" ";GET', 'xy\n'),
                         '       120 y 13\n')

    def test_inkey_gives_waiting_keys_then_minus_one(self):
        self.assertEqual(self.run_typed('k=GET:PRINT INKEY(0);" ";INKEY(1);" ";INKEY(0)', 'ab\n'),
                         '        98 13 -1\n')

    def test_inkey_string_and_negative_inkey(self):
        self.assertEqual(self.run_bbc('PRINT "[";INKEY$(0);"]";INKEY(-99)'), '[]0\n')

    def test_keys_from_the_graphics_window(self):
        keys = iter([65, -1, -1, 139])
        lispy3.global_env['graphics-key'] = lambda: next(keys)
        self.assertEqual(self.run_bbc('PRINT GET;" ";INKEY(0);" ";GET'), '        65 -1 139\n')


class MBasicNamesTest(ReaderTestCase):

    def run_mbasic(self, source):
        self.ev('(bbc-set-print-style! :mbasic)')
        try:
            return self.run_bbc(source)
        finally:
            self.ev('(bbc-set-print-style! :bbc)')

    def test_assigned_keywords_are_variables_in_mbasic(self):
        self.assertEqual(self.run_mbasic('10 COUNT = 0\n20 COUNT = COUNT + 1\n30 PI = 3\n'
                                         '40 PRINT COUNT; PI'), ' 1  3 \n')

    def test_unassigned_pi_stays_the_constant(self):
        self.assertEqual(self.run_mbasic('PRINT PI > 3'), '-1 \n')

    def test_bbc_style_still_rejects_keyword_names(self):
        with self.assertRaises(Exception):
            self.run_bbc('COUNT = 1')


if __name__ == '__main__':
    unittest.main()
