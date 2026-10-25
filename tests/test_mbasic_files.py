"""MBASIC sequential text files in mini-basic: OPEN, PRINT #, WRITE #, INPUT #,
LINE INPUT #, EOF(n) and CLOSE, on top of lispy3's text streams."""
import contextlib
import io
import os
import tempfile

from support import LispyTestCase, lispy3


class MBasicFilesTest(LispyTestCase):

    def setUp(self):
        super().setUp()
        lispy3.load_workspace('mini-basic')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, 'data.txt').replace('\\', '/')

    def run_bbc(self, source):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-run """' + source.replace('FILE', self.path) + '\n""")')
        return out.getvalue()

    def text(self):
        with open(self.path, encoding='utf-8') as f:
            return f.read()

    def test_print_and_line_input(self):
        out = self.run_bbc('OPEN "O", #1, "FILE"\nPRINT #1, "Line 1"\nPRINT #1, "N:"; 10; -2\nCLOSE 1\n'
                           'OPEN "I", 1, "FILE"\nLINE INPUT #1, L$\nPRINT L$\nLINE INPUT #1, L$\nPRINT L$\nCLOSE')
        self.assertEqual(self.text(), 'Line 1\nN:10-2\n')
        self.assertEqual(out, 'Line 1\nN:10-2\n')

    def test_print_uses_the_mbasic_number_spaces(self):
        self.ev('(bbc-set-print-style! :mbasic)')
        try:
            self.run_bbc('OPEN "O", 1, "FILE" : PRINT #1, "N:"; 10; -2 : CLOSE #1')
        finally:
            self.ev('(bbc-set-print-style! :bbc)')
        self.assertEqual(self.text(), 'N: 10 -2 \n')

    def test_append_eof_and_for_as_form(self):
        out = self.run_bbc('OPEN "FILE" FOR OUTPUT AS #2 : PRINT #2, "a" : CLOSE #2\n'
                           'OPEN "A", 2, "FILE" : PRINT #2, "b" : CLOSE\n'
                           'OPEN "FILE" FOR INPUT AS 3\nWHILE NOT EOF(3)\nLINE INPUT #3, L$ : PRINT L$\nENDWHILE\nCLOSE 3')
        self.assertEqual(out, 'a\nb\n')

    def test_write_and_input_fields(self):
        out = self.run_bbc('OPEN "O", 1, "FILE"\nWRITE #1, "Alice, A.", 25, 1250.5\nWRITE #1, "Bob", 30, 7\nCLOSE 1\n'
                           'OPEN "I", 1, "FILE"\nINPUT #1, N$, A, S\nPRINT N$;"|";A;"|";S\n'
                           'INPUT #1, N$, A, S\nPRINT N$;"|";A;"|";S\nCLOSE 1')
        self.assertEqual(self.text(), '"Alice, A.",25,1250.5\n"Bob",30,7\n')
        self.assertEqual(out, 'Alice, A.|25|1250.5\nBob|30|7\n')

    def test_print_columns_and_trailing_semicolon_in_a_file(self):
        self.run_bbc('OPEN "O", 1, "FILE" : PRINT #1, "ab"; : PRINT "screen" : PRINT #1, "cd"\nCLOSE')
        self.assertEqual(self.text(), 'abcd\n')

    def test_errors(self):
        for source, message in [('OPEN "I", 1, "FILE"', 'File not found'),
                                ('OPEN "R", 1, "FILE"', 'Random files'),
                                ('PRINT #4, "x"', 'channel 4'),
                                ('OPEN "O", 1, "FILE" : OPEN "O", 1, "FILE"', 'already open')]:
            with self.subTest(source=source), self.assertRaisesRegex(Exception, message):
                self.run_bbc(source)
            self.run_bbc('CLOSE')

    def test_line_input_from_the_keyboard_is_input_line(self):
        self.assertEqual(lispy3.lisp_str(self.ev('(bbc-expand "LINE INPUT \\"Name\\"; A$")')),
                         lispy3.lisp_str(self.ev('(bbc-expand "INPUT LINE \\"Name\\"; A$")')))

    def test_bbc_binary_channels_still_work(self):
        out = self.run_bbc('F% = OPENOUT "FILE" : PRINT#F%, "text", 42 : CLOSE#F%\n'
                           'F% = OPENIN "FILE" : INPUT#F%, a$, n% : CLOSE#F% : PRINT a$;n%')
        self.assertEqual(out, 'text42\n')
