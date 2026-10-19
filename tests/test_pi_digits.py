"""The pi_digits.lisp example prints the right digits of pi."""
import contextlib
import io
import os
import unittest

from support import LispyTestCase, lispy3


def python_pi(decimals: int) -> str:
    """Pi to `decimals` places with Machin's formula in Python whole numbers."""
    scale = 10 ** (decimals + 10)

    def arctan_inv(x: int) -> int:
        total = term = scale // x
        k, sign = 1, 1
        while term:
            term //= x * x
            sign = -sign
            total += sign * (term // (2 * k + 1))
            k += 1
        return total

    digits = str(4 * (4 * arctan_inv(5) - arctan_inv(239)))[:decimals + 1]
    return digits[0] + '.' + digits[1:]


class PiDigitsTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertTrue(lispy3.run_file(os.path.join(lispy3.LISP_DIR, 'pi_digits.lisp')))
        self.printed = out.getvalue().strip()

    def test_program_prints_100_decimals(self):
        """lisp/pi-digits.lisp prints the first 100 decimals of pi correctly."""
        self.assertEqual(self.printed, python_pi(100))

    def test_other_lengths(self):
        """pi-digits is right for 1, 5, 31 and 50 decimals too."""
        for decimals in (1, 5, 31, 50):
            with self.subTest(decimals=decimals):
                self.assertEqual(self.ev(f'(pi-digits {decimals})').value, python_pi(decimals))


if __name__ == '__main__':
    unittest.main()
