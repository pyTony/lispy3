"""Number literals in the mini-basic reader: exponents and a leading point.

PRINT ; turns off the right-justified number field, as in BBC BASIC.
"""
from test_mini_basic_reader import ReaderTestCase


class NumberLiteralTest(ReaderTestCase):

    def test_exponent(self):
        self.assertEqual(self.run_bbc('x = 1E5 : PRINT ;x'), '100000\n')

    def test_signed_exponent(self):
        self.assertEqual(self.run_bbc('PRINT ;25E-1;" ";1.5E+2'), '2.5 150\n')

    def test_leading_point(self):
        self.assertEqual(self.run_bbc('PRINT ;.5 + .25'), '0.75\n')

    def test_e_after_a_number_without_digits_is_not_an_exponent(self):
        self.assertEqual(self.run_bbc('E = 3 : PRINT ;2*E'), '6\n')


if __name__ == '__main__':
    import unittest
    unittest.main()
