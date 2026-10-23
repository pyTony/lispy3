"""Common Lisp style byte streams in lispy3: open-file, read-byte, write-byte,
file-position, file-length and close."""
import os
import tempfile

from support import LispyTestCase


class BinaryFileTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'bytes.bin').replace('\\', '/')

    def tearDown(self):
        self.dir.cleanup()
        super().tearDown()

    def test_write_then_read_bytes(self):
        self.ev_all(f'(define f (open-file "{self.path}" "wb"))',
                    '(write-byte 65 f)', '(write-byte 300 f)', '(close f)')
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), b'A,')  # 300 modulo 256 is 44
        self.ev(f'(define f (open-file "{self.path}" "rb"))')
        self.assertEqual(self.ev('(read-byte f)'), 65)
        self.assertEqual(self.ev('(read-byte f)'), 44)
        self.assertIs(self.ev('(read-byte f)'), False)
        self.assertEqual(self.ev('(read-byte f :eof)'), ':eof')
        self.ev('(close f)')

    def test_position_and_length(self):
        with open(self.path, 'wb') as f:
            f.write(b'xyz')
        self.ev(f'(define f (open-file "{self.path}" "r+b"))')
        self.assertEqual(self.ev('(file-length f)'), 3)
        self.assertEqual(self.ev('(file-position f)'), 0)
        self.ev('(file-position f 2)')
        self.assertEqual(self.ev('(read-byte f)'), ord('z'))
        self.ev_all('(write-byte 33 f)', '(close f)')
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), b'xyz!')

    def test_file_length_does_not_move(self):
        with open(self.path, 'wb') as f:
            f.write(b'abcd')
        self.ev_all(f'(define f (open-file "{self.path}" "rb"))', '(read-byte f)', '(file-length f)')
        self.assertEqual(self.ev('(file-position f)'), 1)
        self.ev('(close f)')

    def test_text_modes_are_refused(self):
        with self.assertRaisesRegex(Exception, 'not binary'):
            self.ev(f'(open-file "{self.path}" "w")')

    def test_a_missing_file_raises_an_error_try_can_catch(self):
        missing = self.path + '.missing'
        self.assertEqual(self.ev(f'(try (open-file "{missing}" "rb") (catch e "none"))').value, 'none')
