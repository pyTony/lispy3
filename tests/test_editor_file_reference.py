from unittest import TestCase
import editor_tools as ET

class FileReferenceTest(TestCase):
    def test_quoted_lisp_filename_and_comment(self):
        text = '(load "folder/file name.lisp") ; "ignored.lisp"'
        self.assertEqual(ET.file_reference_at_cursor(text, 15, 'Lisp'), 'folder/file name.lisp')
        self.assertIsNone(ET.file_reference_at_cursor(text, text.index('ignored'), 'Lisp'))
    def test_python_raw_filename(self):
        self.assertEqual(ET.file_reference_at_cursor('open(r"C:\\demo.bas")', 12, 'Python'), r'C:\demo.bas')
    def test_basic_escaped_quotes(self):
        self.assertEqual(ET.file_reference_at_cursor('LOAD "a""b.bas"', 9, 'BBC BASIC'), 'a"b.bas')

    def test_existing_buffer_is_selected_without_reloading_edits(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        import os
        app = Mock(); tab = Mock(); tab.path = os.path.abspath('edited.lisp')
        app.tabs = {'edited.lisp': tab}
        machine.LispMachine._open_source_path(app, tab.path)
        app.notebook.select.assert_called_once_with(tab)
        app.new_buffer.assert_not_called()
