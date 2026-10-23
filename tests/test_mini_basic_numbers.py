"""Numbers in the mini-basic reader: literals, number types and the
BBC BASIC for SDL integer extensions.

PRINT ; turns off the right-justified number field, as in BBC BASIC.
Integer variables: A% 32-bit, A%% 64-bit, A& an unsigned byte, A# a float.
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

    def test_binary(self):
        self.assertEqual(self.run_bbc('PRINT ;%1010;" ";&10 + %11;" ";%0'), '10 19 0\n')

    def test_hex_is_a_32_bit_signed_number(self):
        self.assertEqual(self.run_bbc('PRINT ;&FF;" ";&FFFFFFFF;" ";&7FFFFFFF;" ";&80000000'),
                         '255 -1 2147483647 -2147483648\n')


class ArithmeticTest(ReaderTestCase):
    """How the number types behave today; these already passed."""

    def test_division(self):
        self.assertEqual(self.run_bbc('PRINT ;7/2;" ";6/2;" ";1/3'), '3.5 3 0.333333333\n')

    def test_div_and_mod_round_toward_zero(self):
        self.assertEqual(self.run_bbc('PRINT ;7 DIV 2;" ";-7 DIV 2;" ";-7 MOD 2;" ";7 MOD -2'),
                         '3 -3 -1 1\n')

    def test_power_and_int(self):
        self.assertEqual(self.run_bbc('PRINT ;2^10;" ";2^0.5;" ";INT(-3.5)'), '1024 1.41421356 -4\n')

    def test_big_numbers(self):
        self.assertEqual(self.run_bbc('PRINT ;1E10;" ";2147483647+1'), '1E10 2147483648\n')

    def test_logic_is_bitwise_on_integers(self):
        self.assertEqual(self.run_bbc('PRINT ;TRUE AND 5;" ";NOT 0;" ";5 EOR 3;" ";5 OR 2'),
                         '5 -1 6 7\n')


class ShiftTest(ReaderTestCase):

    def test_shifts(self):
        self.assertEqual(self.run_bbc('PRINT ;1 << 4;" ";256 >> 4;" ";-16 >> 2'), '16 16 -4\n')

    def test_logical_shift_right_is_32_bit(self):
        # BBCSDL 1.44a: -16 >>> 28 is 15
        self.assertEqual(self.run_bbc('PRINT ;-16 >>> 28;" ";256 >>> 4'), '15 16\n')

    def test_shifts_bind_like_comparisons(self):
        self.assertEqual(self.run_bbc('PRINT ;1 << 2 + 1;" ";(1 << 3 = 8)'), '8 -1\n')


class HexOutputTest(ReaderTestCase):

    def test_print_tilde(self):
        self.assertEqual(self.run_bbc('PRINT ;~255;" ";~-1'), 'FF FFFFFFFF\n')

    def test_print_tilde_right_justifies(self):
        self.assertEqual(self.run_bbc('PRINT ~255'), '        FF\n')

    def test_print_tilde_applies_to_one_item(self):
        # BBCSDL 1.44a prints FF and then 255 in the next zone
        self.assertEqual(self.run_bbc('PRINT ~255, 255'), '        FF       255\n')

    def test_str_tilde(self):
        self.assertEqual(self.run_bbc('a$ = STR$~255 + "/" + STR$~-2 + "/" + STR$(255) : PRINT a$'),
                         'FF/FFFFFFFE/255\n')


class VariableTypeTest(ReaderTestCase):

    def test_integer_variable_truncates(self):
        self.assertEqual(self.run_bbc('A% = 3.7 : B% = -3.7 : PRINT ;A%;" ";B%'), '3 -3\n')

    def test_integer_variable_range(self):
        self.assertEqual(self.run_bbc('A% = 2147483647 : B% = -2147483648 : PRINT ;A%;" ";B%'),
                         '2147483647 -2147483648\n')

    def test_integer_variable_too_big(self):
        with self.assertRaisesRegex(Exception, 'Number too big'):
            self.run_bbc('A% = 2^31')

    def test_64_bit_integer_variable(self):
        self.assertEqual(self.run_bbc('A%% = 2^40 : B%% = 1.9 : PRINT ;A%%;" ";B%%;" ";A%% >> 8'),
                         '1099511627776 1 4294967296\n')

    def test_byte_variable_keeps_the_low_byte(self):
        self.assertEqual(self.run_bbc('b& = 300 : c& = -1 : PRINT ;b&;" ";c&'), '44 255\n')

    def test_float_variable(self):
        self.assertEqual(self.run_bbc('x# = 1/4 : y# = 3 : PRINT ;x#;" ";y#'), '0.25 3\n')

    def test_suffixes_name_different_variables(self):
        self.assertEqual(self.run_bbc('a = 1 : a% = 2 : a%% = 3 : a& = 4 : a# = 5 : a$ = "s"\n'
                                      'PRINT ;a;a%;a%%;a&;a#;a$'),
                         '12345s\n')


if __name__ == '__main__':
    import unittest
    unittest.main()
