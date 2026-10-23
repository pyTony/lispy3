"""Bit operations: #b/#x/#o literals and the bitwise library (lisp/bitwise.sld).

Names follow Scheme (R7RS literals, SRFI 151 procedures), with the Common Lisp
names as aliases, the way lispy3 already pairs remainder with rem.
"""
from support import LispyTestCase, lispy3


class RadixLiteralTest(LispyTestCase):

    def test_binary_hex_and_octal(self):
        self.assertEqual(self.ev('(list #b1010 #xFF #xff #o17 #b-101 #x-10)'),
                         [10, 255, 255, 15, -5, -16])

    def test_bad_digits_are_an_error(self):
        with self.assertRaises(Exception):
            self.ev('#b102')


class BitwiseLibraryTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        lispy3.library_system.reset()
        self.ev('(import (prefix bitwise b:))')

    def test_logic(self):
        self.assertEqual(self.ev('(list (b:bitwise-and 12 10) (b:bitwise-ior 12 10) '
                                 '(b:bitwise-xor 12 10) (b:bitwise-not 0))'),
                         [8, 14, 6, -1])

    def test_logic_takes_any_number_of_arguments(self):
        self.assertEqual(self.ev('(list (b:bitwise-and) (b:bitwise-ior) (b:bitwise-and 7 6 4) '
                                 '(b:bitwise-xor 1 2 4))'),
                         [-1, 0, 4, 7])

    def test_arithmetic_shift(self):
        self.assertEqual(self.ev('(list (b:arithmetic-shift 1 4) (b:arithmetic-shift 256 -4) '
                                 '(b:arithmetic-shift -16 -2))'),
                         [16, 16, -4])

    def test_common_lisp_names(self):
        self.assertEqual(self.ev('(list (b:logand 12 10) (b:logior 12 10) (b:logxor 12 10) '
                                 '(b:lognot 5) (b:ash 1 10) (b:logcount 255) (b:logbitp 3 8))'),
                         [8, 14, 6, -6, 1024, 8, True])

    def test_bit_count_length_and_set(self):
        self.assertEqual(self.ev('(list (b:bit-count 255) (b:bit-count -1) (b:integer-length 255) '
                                 '(b:integer-length -1) (b:bit-set? 3 8) (b:bit-set? 2 8))'),
                         [8, 0, 8, 0, True, False])

    def test_bit_field_is_unsigned(self):
        self.assertEqual(self.ev('(list (b:bit-field #xABCD 4 12) (b:bit-field -1 0 32))'),
                         [0xBC, 0xFFFFFFFF])

    def test_signed_field_wraps_to_twos_complement(self):
        self.assertEqual(self.ev('(list (b:signed-field #xFFFFFFFF 32) (b:signed-field #x7FFFFFFF 32) '
                                 '(b:signed-field 300 8) (b:signed-field #x80000000 32))'),
                         [-1, 0x7FFFFFFF, 44, -0x80000000])

    def test_logical_shift_right_of_a_fixed_width(self):
        self.assertEqual(self.ev('(list (b:logical-shift-right -16 28 32) (b:logical-shift-right 256 4 32))'),
                         [15, 16])

    def test_number_text_in_a_base(self):
        self.assertEqual(str(self.ev('(number->string #b1010 2)')), '1010')
        self.assertEqual(self.ev('(string->number "ff" 16)'), 255)

    def test_whole_numbers_only(self):
        with self.assertRaises(Exception):
            self.ev('(b:bitwise-and 1.5 1)')


if __name__ == '__main__':
    import unittest
    unittest.main()
