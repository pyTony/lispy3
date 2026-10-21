from unittest import TestCase
import syntax_highlight as SH


class EditorToolsTest(TestCase):
    def test_basic_highlights_keywords_strings_and_comments(self):
        languages, errors = SH.load_languages()
        self.assertEqual(errors, [])
        basic = SH.language_for('demo.BAS', languages)
        self.assertIsNotNone(basic)
        text = 'for I%=1 TO 2: PRINT "REM NEXT": REM FOR I%'
        spans = [(tag, text[a:b]) for tag,a,b in basic.spans(text)]
        self.assertIn(('special', 'for'), spans)
        self.assertIn(('string', '"REM NEXT"'), spans)
        self.assertIn(('comment', 'REM FOR I%'), spans)

    def test_lisp_check_has_location_and_does_not_execute(self):
        from editor_tools import check_lisp
        check_lisp('(display "not executed") ; )\n[1 2]')
        with self.assertRaises(SyntaxError) as caught:
            check_lisp('(begin\n  ]', 'demo.lisp')
        self.assertEqual((caught.exception.lineno, caught.exception.offset), (2, 3))
        self.assertIn('demo.lisp', str(caught.exception))

    def test_missing_close_and_unterminated_string_are_reported(self):
        from editor_tools import check_lisp
        for text in ['(begin\n  1', '(display "unfinished)', '(display """unfinished)', "'"]:
            with self.subTest(text=text), self.assertRaises(SyntaxError):
                check_lisp(text)

    def test_lisp_indent_preserves_multiline_strings_and_comments(self):
        from editor_tools import indent_lisp
        text = '(begin\n(display """raw\n  keep these spaces\n""") ; comment\n[1\n2])\n'
        expected = '(begin\n  (display """raw\n  keep these spaces\n""") ; comment\n  [1\n    2])\n'
        self.assertEqual(indent_lisp(text), expected)
        self.assertEqual(indent_lisp(expected), expected)

    def test_invalid_lisp_is_not_formatted(self):
        from editor_tools import indent_lisp
        with self.assertRaises(SyntaxError):
            indent_lisp('(begin\n  ]')

    def test_basic_indent_nested_blocks_and_inline_statements(self):
        from editor_tools import indent_basic
        text = 'FOR I%=1 TO 3\nIF I%=2 THEN\nPRINT "NEXT:ENDIF"\nELSE\nREPEAT\nPRINT I%\nUNTIL TRUE\nENDIF\nNEXT\nFOR J%=1 TO 2:PRINT J%:NEXT\nPRINT "done"\n'
        expected = 'FOR I%=1 TO 3\n  IF I%=2 THEN\n    PRINT "NEXT:ENDIF"\n  ELSE\n    REPEAT\n      PRINT I%\n    UNTIL TRUE\n  ENDIF\nNEXT\nFOR J%=1 TO 2:PRINT J%:NEXT\nPRINT "done"\n'
        self.assertEqual(indent_basic(text), expected)
        self.assertEqual(indent_basic(expected), expected)

    def test_basic_line_numbers_and_return_indent(self):
        from editor_tools import indent_basic, next_indent
        self.assertEqual(indent_basic('10 FOR I%=1 TO 2\n20 PRINT I%\n30 NEXT'),
                         '10 FOR I%=1 TO 2\n20   PRINT I%\n30 NEXT')
        self.assertEqual(next_indent('FOR I%=1 TO 2', basic=True), 2)
        self.assertEqual(next_indent('(begin\n(display "(") ; ('), 2)


class EditorCommandsTest(TestCase):
    def app(self, source, language='Lisp'):
        from test_machine_eval_buffer import _FakeMachine
        from test_machine_args import machine
        from unittest.mock import Mock
        app = _FakeMachine(source)
        app.tab.path = None
        app.tab.language = Mock(name='language')
        app.tab.language.name = language
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ()
        app.tab.text.index.return_value = '2.0'
        app.tab._schedule_highlight = Mock()
        app._editor_syntax_error = lambda tab,error: machine.LispMachine._editor_syntax_error(app, tab, error)
        return app, machine

    def test_check_jumps_to_error_without_modifying_buffer(self):
        app, machine = self.app('(begin\n ]')
        machine.LispMachine.check_buffer_syntax(app)
        app.tab.text.mark_set.assert_called_with('insert', '2.1')
        app.tab.text.delete.assert_not_called()
        self.assertIn('test.lisp', ''.join(app.lines))
        app.tab.text.tag_add.assert_called_with('syntax_error', '2.1', '2.1+1c')

    def test_reindent_groups_edit_and_preserves_other_lines(self):
        app, machine = self.app('(begin\n(display 1)\n(display 2))\n')
        app.tab.text.tag_ranges.return_value = ('2.0', '3.0')
        machine.LispMachine.reindent_buffer(app)
        app.tab.text.insert.assert_called_once_with('1.0', '(begin\n  (display 1)\n(display 2))\n')
        self.assertEqual(app.tab.text.edit_separator.call_count, 2)
        app.tab.text.configure.assert_any_call(autoseparators=False)

    def test_invalid_buffer_is_not_edited(self):
        app, machine = self.app('(begin\n]')
        machine.LispMachine.reindent_buffer(app)
        app.tab.text.delete.assert_not_called()
        app.tab.text.insert.assert_not_called()
