"""BBC BASIC file I/O in the mini-basic reader: OPENIN, OPENOUT, OPENUP,
PRINT#, INPUT#, BPUT#, BGET#, GET$#, EOF#, PTR#, EXT# and CLOSE#.

Byte layouts follow BBC BASIC for SDL: PRINT# ends a string with CR, and
BPUT# of a string ends it with LF. Numbers written by PRINT# are only checked
to read back with INPUT#.
"""
import os
import tempfile

from support import lispy3
from test_mini_basic_reader import ReaderTestCase


class FileIOTest(ReaderTestCase):

    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'data.dat')

    def tearDown(self):
        self.dir.cleanup()
        super().tearDown()

    def file_bytes(self) -> bytes:
        with open(self.path, 'rb') as f:
            return f.read()

    def test_print_and_input_round_trip(self):
        source = (f'F% = OPENOUT "{self.path}"\n'
                  'PRINT#F%, "hello, world", 42, 2.5\n'
                  'CLOSE#F%\n'
                  f'F% = OPENIN "{self.path}"\n'
                  'INPUT#F%, a$, n%, x\n'
                  'PRINT a$;"/";n%;"/";x;"/";EOF#F%\n'
                  'CLOSE#F%')
        self.assertEqual(self.run_bbc(source), 'hello, world/42/2.5/-1\n')

    def test_print_hash_ends_a_string_with_cr(self):
        self.run_bbc(f'F% = OPENOUT "{self.path}" : PRINT#F%, "AB", "C" : CLOSE#F%')
        self.assertEqual(self.file_bytes(), b'AB\rC\r')

    def test_bput_writes_bytes_and_strings_with_lf(self):
        self.run_bbc(f'F% = OPENOUT "{self.path}" : BPUT#F%, 65 : BPUT#F%, "hi" : '
                     'BPUT#F%, "x"; : CLOSE#F%')
        self.assertEqual(self.file_bytes(), b'Ahi\nx')

    def test_bget_reads_bytes_until_eof(self):
        with open(self.path, 'wb') as f:
            f.write(b'AB\n')
        source = (f'F% = OPENIN "{self.path}"\n'
                  'WHILE NOT EOF#F% : PRINT ;BGET#F%;" "; : ENDWHILE\n'
                  'CLOSE#F% : PRINT')
        self.assertEqual(self.run_bbc(source), '65 66 10 \n')

    def test_get_dollar_reads_a_line(self):
        with open(self.path, 'wb') as f:
            f.write(b'first line\nsecond\r\n')
        source = (f'F% = OPENIN "{self.path}"\n'
                  'a$ = GET$#F% : b$ = GET$#F%\n'
                  'PRINT "[";a$;"][";b$;"]";EOF#F%\n'
                  'CLOSE#F%')
        self.assertEqual(self.run_bbc(source), '[first line][second]-1\n')

    def test_openin_of_a_missing_file_gives_zero(self):
        missing = os.path.join(self.dir.name, 'missing.dat')
        self.assertEqual(self.run_bbc(f'PRINT ;OPENIN "{missing}"'), '0\n')

    def test_openup_ptr_and_ext(self):
        with open(self.path, 'wb') as f:
            f.write(b'xyz')
        source = (f'F% = OPENUP "{self.path}"\n'
                  'PRINT ;EXT#F%;" ";PTR#F%\n'
                  'PTR#F% = 1 : PRINT ;BGET#F%\n'
                  'PTR#F% = 3 : BPUT#F%, 33\n'
                  'PRINT ;EXT#F%\n'
                  'CLOSE#F%')
        self.assertEqual(self.run_bbc(source), '3 0\n121\n4\n')
        self.assertEqual(self.file_bytes(), b'xyz!')

    def test_close_hash_zero_closes_every_file(self):
        with self.assertRaisesRegex(Exception, 'channel'):
            self.run_bbc(f'F% = OPENOUT "{self.path}" : CLOSE#0 : BPUT#F%, 65')

    def test_numbers_of_every_kind_read_back(self):
        source = (f'F% = OPENOUT "{self.path}"\n'
                  'PRINT#F%, -7, 3000000000, -0.125, 1/3, 0\n'
                  'PTR#F% = 0\n'
                  'INPUT#F%, a, b, c, d, e\n'
                  'CLOSE#F%\n'
                  'PRINT ;a;" ";b;" ";c;" ";d;" ";e')
        self.assertEqual(self.run_bbc(source), '-7 3E9 -0.125 0.333333333 0\n')

    def test_input_hash_into_an_array_element(self):
        source = (f'F% = OPENOUT "{self.path}" : PRINT#F%, 5, "five" : PTR#F% = 0\n'
                  'DIM n(2), n$(2)\n'
                  'INPUT#F%, n(1), n$(2)\n'
                  'CLOSE#F%\n'
                  'PRINT ;n(1);" ";n$(2)')
        self.assertEqual(self.run_bbc(source), '5 five\n')

    def test_a_function_that_reads_a_file_is_not_remembered(self):
        with open(self.path, 'wb') as f:
            f.write(b'AB')
        source = (f'F% = OPENIN "{self.path}"\n'
                  'PRINT ;FNnext(F%);" ";FNnext(F%)\n'
                  'CLOSE#F%\nEND\n'
                  'DEF FNnext(c) = BGET#c')
        self.assertEqual(self.run_bbc(source), '65 66\n')


class FileIOHookTest(ReaderTestCase):
    """mini-basic-io.lisp wraps the reader's hooks: file forms go to it, everything else
    still reaches mini-basic-ext.lisp and mini-basic.lisp."""

    def test_hash_statements_and_functions_become_file_calls(self):
        self.assertEqual(self.expand('PRINT#F%, 1, "a"'), '(bbc-program (bbc-print-file F% 1 "a"))')
        self.assertEqual(self.expand('BPUT#F%, 7;'), '(bbc-program (bbc-bput F% 7 #f))')
        self.assertEqual(self.expand('x = EOF#F%'), '(bbc-program (LET x (bbc-eof F%)))')
        self.assertEqual(self.expand('F% = OPENIN "a"'), '(bbc-program (LET F% (bbc-open "a" "rb")))')

    def test_print_without_hash_is_left_to_the_reader(self):
        self.assertNotIn('bbc-print-file', self.expand('PRINT 1'))

    def test_ext_statements_still_work_next_to_file_io(self):
        path = os.path.join(tempfile.mkdtemp(), 'x.dat')
        source = (f'F% = OPENOUT "{path}"\n'
                  'DIM a(2) : READ a(1), a(2)\n'
                  'GOSUB 100\n'
                  'CLOSE#F%\n'
                  f'F% = OPENIN "{path}" : INPUT#F%, s : CLOSE#F%\n'
                  'PRINT ;s\n'
                  'END\n'
                  '100 PRINT#F%, a(1) + a(2) : RETURN\n'
                  'DATA 3, 4')
        self.assertEqual(self.run_bbc(source), '7\n')
        os.unlink(path)

    def test_a_pure_function_is_still_remembered(self):
        self.run_bbc('PRINT FNsq(3)\nEND\nDEF FNsq(n) = n*n')
        self.assertNotIsInstance(self.ev('FN-sq'), lispy3.Procedure)

    def test_a_function_using_a_channel_is_not_remembered(self):
        self.run_bbc('x = 1\nEND\nDEF FNb(c) = BGET#c')
        self.assertIsInstance(self.ev('FN-b'), lispy3.Procedure)
