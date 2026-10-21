from unittest import TestCase
from support import lispy3


class ReaderErrorLocationTest(TestCase):
    def test_extra_closer_after_multiline_string_and_comment(self):
        source = '; ignored )\n(display """first\nsecond )""")\n  )'
        tokens = lispy3.tokenize(source)
        lispy3.read_from_tokens(tokens)
        with self.assertRaisesRegex(SyntaxError, r'line 4, column 3') as caught:
            lispy3.read_from_tokens(tokens)
        self.assertEqual(caught.exception.lineno, 4)
        self.assertEqual(caught.exception.offset, 3)

    def test_named_source_is_in_diagnostic(self):
        tokens = lispy3.tokenize('  ]', source_name='example.lisp')
        with self.assertRaisesRegex(SyntaxError, 'example.lisp') as caught:
            lispy3.read_from_tokens(tokens)
        self.assertEqual(caught.exception.filename, 'example.lisp')

    def test_plain_token_lists_still_work(self):
        with self.assertRaisesRegex(SyntaxError, 'Unexpected closing bracket'):
            lispy3.read_from_tokens([')'])
