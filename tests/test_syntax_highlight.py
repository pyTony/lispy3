"""Tests for the editor's syntax colouring rules (no tkinter needed).

Run:  python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import syntax_highlight as SH

LANGS, ERRORS = SH.load_languages()
LISP = SH.language_for("x.lisp", LANGS)
PYTHON = SH.language_for("x.py", LANGS)


def colours(lang, text, **kw):
    return [(tag, text[s:e]) for tag, s, e in lang.spans(text, **kw)]


class LispColours(unittest.TestCase):
    def test_files_load(self):
        """The Lisp and Python syntax files load without errors."""
        self.assertEqual(ERRORS, [])
        self.assertEqual((LISP.name, PYTHON.name), ("Lisp", "Python"))
        self.assertEqual(LISP.line_comment, ";")

    def test_semicolon_in_string_is_not_a_comment(self):
        """A ; inside a string is coloured as string, the real comment as comment."""
        self.assertEqual(colours(LISP, '(display "a; b") ; note "x"'), [
            ("string", '"a; b"'), ("comment", '; note "x"')])

    def test_escaped_quote_and_raw_string(self):
        """Escaped quotes and triple-quoted raw strings stay one string each."""
        text = '"say \\"hi\\" ; ok" """raw "q" ; no\nline 2"""'
        self.assertEqual([t for t, _ in colours(LISP, text)], ["string", "string"])

    def test_unterminated_string_runs_to_the_end(self):
        """An unclosed string is coloured to the end of the text."""
        self.assertEqual(colours(LISP, '"open ; (x)\n(y)'), [("string", '"open ; (x)\n(y)')])

    def test_atoms(self):
        """Special forms, constants, characters, keywords, numbers, built-ins and variables."""
        text = "(if #t #\\; :key -1.5e3 1+ x-1 #f)"
        self.assertEqual(colours(LISP, text, builtins={"1+"}, variables={"x-1"}), [
            ("special", "if"), ("constant", "#t"), ("char", "#\\;"), ("keyword", ":key"),
            ("number", "-1.5e3"), ("builtin", "1+"), ("variable", "x-1"), ("constant", "#f")])

    def test_brackets_inside_strings_are_masked(self):
        """Brackets inside strings and comments are not used for bracket matching."""
        text = '(f "(") ; )'
        mask = SH.code_mask(LISP.spans(text), len(text))
        self.assertEqual([i for i, c in enumerate(text) if c in "()" and not mask[i]], [0, 6])


class PythonColours(unittest.TestCase):
    def test_python(self):
        """Python keywords, function names, comments, strings and decorators."""
        text = 'def f(self):  # c "q"\n    return f"a#b" is None\n@deco\nclass A: pass'
        self.assertEqual(colours(PYTHON, text), [
            ("keyword", "def"), ("function", "f"), ("variable", "self"),
            ("comment", '# c "q"'), ("keyword", "return"), ("string", 'f"a#b"'),
            ("keyword", "is"), ("constant", "None"), ("decorator", "@deco"),
            ("keyword", "class"), ("function", "A"), ("keyword", "pass")])

    def test_extension_picks_language(self):
        """The file extension picks the language, in any case."""
        self.assertIs(SH.language_for("tool.PYW", LANGS), PYTHON)
        self.assertIsNone(SH.language_for("notes.txt", LANGS))


if __name__ == "__main__":
    unittest.main()


class BasicCommentColours(unittest.TestCase):
    def test_rem_does_not_require_following_space(self):
        basic=SH.language_for('program.bas',LANGS)
        for source in ('10 REMM THIS IS COMMENT', '10REMM THIS IS COMMENT',
                       'PRINT 1:REMcomment "not a string', 'remcomment'):
            with self.subTest(source=source):
                spans=colours(basic,source)
                self.assertEqual([text for tag,text in spans if tag == 'comment'],
                                 [source[source.upper().index('REM'):]])

    def test_rem_inside_string_or_identifier_is_not_a_comment(self):
        basic=SH.language_for('program.bas',LANGS)
        self.assertEqual([text for tag,text in colours(basic,'PRINT "REMM":PREM=7')
                          if tag == 'comment'],[])
