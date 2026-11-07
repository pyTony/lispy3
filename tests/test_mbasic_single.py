"""MBASIC single precision in mini-basic: the ! suffix, singles printed with 6
digits in the MBASIC print style (bbc-single-precision turns it off), and WEND."""
import contextlib
import io

from support import LispyTestCase, lispy3


class MBasicSingleTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        lispy3.load_workspace('mini-basic')
        self.addCleanup(lambda: self.ev('(bbc-set-print-style! :bbc)'))

    def run_bbc(self, source, style=':mbasic'):
        self.ev(f'(bbc-set-print-style! {style})')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-run """' + source + '\n""")')
        return out.getvalue()

    def test_singles_print_with_six_digits(self):
        self.assertEqual(self.run_bbc('PRINT 1/3 : PRINT 3.14159265*25 : PRINT -2/3 : PRINT 2.5'),
                         ' .333333 \n 78.5398 \n-.666667 \n 2.5 \n')
        self.assertEqual(self.run_bbc('PRINT 1E7/1 : PRINT .00001 : PRINT 4000000/2'),
                         ' 1E+07 \n 1E-05 \n 2000000 \n')
        self.assertEqual(self.run_bbc('PRINT STR$(1/3)'), ' .333333\n')

    def test_the_filter_can_be_turned_off(self):
        self.ev('(set! bbc-single-precision #f)')
        self.assertEqual(self.run_bbc('PRINT 1/3'), ' 0.333333333 \n')

    def test_bbc_style_is_unchanged(self):
        self.assertEqual(self.run_bbc('PRINT 1/3', ':bbc'), '0.333333333\n')

    def test_bang_suffix_rounds_to_single(self):
        self.assertEqual(self.run_bbc('A! = 1/3 : PRINT A!', ':bbc'), '0.333333343\n')
        self.assertEqual(self.ev('(bbc-single 16777217)'), 16777216.0)
        self.assertEqual(self.ev('(bbc-single 0)'), 0.0)

    def test_wend_ends_while_in_mbasic_style(self):
        self.assertEqual(self.run_bbc('I = 0\nWHILE I < 2\nI = I + 1 : PRINT I\nWEND'), ' 1 \n 2 \n')
        with self.assertRaises(Exception):
            self.run_bbc('I = 0\nWHILE I < 2\nI = I + 1\nWEND', ':bbc')
