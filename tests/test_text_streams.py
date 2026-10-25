"""Common Lisp style text streams in lispy3: open, with-open-file, read-line,
write-line, format to a stream, string streams and *standard-output*."""
import contextlib
import io
import os
import tempfile

from support import LispyTestCase, lispy3


class TextFileStreamTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'notes.txt').replace('\\', '/')

    def tearDown(self):
        self.dir.cleanup()
        super().tearDown()

    def text(self):
        with open(self.path, encoding='utf-8') as f:
            return f.read()

    def test_with_open_file_writes_and_reads_lines(self):
        self.ev(f'(with-open-file (s "{self.path}" :direction :output :if-exists :supersede)'
                '  (write-line "hello" s) (format s "x=~a~%" 42) (princ 3.5 s) (terpri s))')
        self.assertEqual(self.text(), 'hello\nx=42\n3.5\n')
        lines = self.ev(f'(with-open-file (s "{self.path}")'
                        '  (list (read-line s) (read-line s) (read-line s) (read-line s nil :eof)))')
        self.assertEqual(lispy3.lisp_str(lines), '("hello" "x=42" "3.5" :eof)')

    def test_read_line_at_end_of_file_is_an_error_by_default(self):
        with open(self.path, 'w') as f:
            f.write('only\n')
        self.assertEqual(self.ev(f'(with-open-file (s "{self.path}") (read-line s)'
                                 ' (try (read-line s) (catch e "eof")))').value, 'eof')

    def test_read_lines_in_a_loop(self):
        with open(self.path, 'w') as f:
            f.write('a\nb\nc')
        result = self.ev(f'(with-open-file (s "{self.path}")'
                         '  (let ((lines ()) (line (read-line s nil #f)))'
                         '    (while line (set! lines (cons line lines)) (set! line (read-line s nil #f)))'
                         '    (reverse lines)))')
        self.assertEqual(lispy3.lisp_str(result), '("a" "b" "c")')

    def test_read_char_and_peek_char(self):
        with open(self.path, 'w') as f:
            f.write('ab')
        result = self.ev(f'(with-open-file (s "{self.path}")'
                         '  (list (peek-char nil s) (read-char s) (read-char s) (read-char s nil :end)))')
        self.assertEqual(lispy3.lisp_str(result), '(#\\a #\\a #\\b :end)')

    def test_append_and_if_exists_error(self):
        self.ev(f'(with-open-file (s "{self.path}" :direction :output) (write-string "one" s))')
        self.ev(f'(with-open-file (s "{self.path}" :direction :output :if-exists :append) (write-string "two" s))')
        self.assertEqual(self.text(), 'onetwo')
        with self.assertRaisesRegex(Exception, 'already exists'):
            self.ev(f'(open "{self.path}" :direction :output :if-exists :error)')

    def test_missing_file(self):
        missing = self.path + '.missing'
        self.assertIs(self.ev(f'(open "{missing}" :if-does-not-exist nil)'), False)
        self.assertEqual(self.ev(f'(try (open "{missing}") (catch e "none"))').value, 'none')

    def test_the_file_is_closed_even_after_an_error(self):
        self.ev(f'(define kept #f)')
        self.ev(f'(try (with-open-file (s "{self.path}" :direction :output) (set! kept s) (error "boom"))'
                ' (catch e #f))')
        self.assertIs(self.ev('(open-stream-p kept)'), False)

    def test_unsigned_byte_element_type_opens_a_binary_file(self):
        self.ev(f'(with-open-file (s "{self.path}" :direction :output :element-type \'(unsigned-byte 8))'
                '  (write-byte 66 s))')
        self.assertEqual(self.ev(f'(with-open-file (s "{self.path}" :element-type \'(unsigned-byte 8))'
                                 ' (read-byte s))'), 66)

    def test_unknown_option_is_reported(self):
        with self.assertRaisesRegex(Exception, 'unknown option'):
            self.ev(f'(open "{self.path}" :mode "w")')


class StringStreamTest(LispyTestCase):

    def test_with_output_to_string(self):
        result = self.ev('(with-output-to-string (s) (write-string "ab" s) (prin1 "q" s) (write-char #\\z s)'
                         ' (format s "~a" 7))')
        self.assertEqual(result.value, 'ab"q"z7')

    def test_with_input_from_string(self):
        self.assertEqual(self.ev('(with-input-from-string (s "one\\ntwo") (read-line s) (read-line s))').value,
                         'two')

    def test_string_output_stream_empties_when_read(self):
        result = self.ev('(let ((o (make-string-output-stream))) (format o "~a" 1)'
                         ' (list (get-output-stream-string o) (get-output-stream-string o)))')
        self.assertEqual(lispy3.lisp_str(result), '("1" "")')

    def test_string_input_stream_range(self):
        self.assertEqual(self.ev('(read-line (make-string-input-stream "hello world" 6))').value, 'world')

    def test_stream_predicates(self):
        self.assertIs(self.ev('(streamp (make-string-output-stream))'), True)
        self.assertIs(self.ev('(streamp "text")'), False)
        self.assertIs(self.ev('(input-stream-p *standard-input*)'), True)
        self.assertIs(self.ev('(output-stream-p *standard-output*)'), True)


class ConsoleStreamTest(LispyTestCase):

    def output(self, code):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.ev(code)
        return out.getvalue()

    def test_standard_output_and_default_stream(self):
        self.assertEqual(self.output('(format *standard-output* "hi ~a~%" 1)'), 'hi 1\n')
        self.assertEqual(self.output('(write-line "plain")'), 'plain\n')
        self.assertEqual(self.output('(begin (princ "a") (terpri) (prin1 "b") (newline))'), 'a\n"b"\n')

    def test_read_line_and_read_char_from_the_console(self):
        lines = iter(['first', 'xy'])
        with lispy3.basic_io.input_from(lambda: next(lines)):
            self.assertEqual(self.ev('(read-line)').value, 'first')
            self.assertEqual(lispy3.lisp_str(self.ev('(list (read-char) (read-char *standard-input*))')),
                             '(#\\x #\\y)')
            self.assertEqual(self.ev('(read-line *standard-input*)').value, '')
