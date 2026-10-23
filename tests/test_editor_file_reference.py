from unittest import TestCase
from lispy_support import editor_tools as ET

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

    def test_windows_path_at_end_of_quoted_listener_input(self):
        path = r'C:\Users\admin\mini_basic\mini_basic\constants.py'
        for quote in ('"', '"""'):
            text = quote + path + quote
            with self.subTest(quote=quote):
                self.assertEqual(ET.file_reference_at_cursor(text, len(text), 'Lisp'), path)

    def test_open_file_uses_focused_listener_input(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        app = Mock()
        app.focus_get.return_value = app.listener_input
        app.basic_repl_mode.get.return_value = False
        app.listener_input.get.return_value = '"example.bas"'
        app.listener_input.index.return_value = 13
        machine.LispMachine.open_file_at_cursor(app)
        app._open_file_reference.assert_called_once_with('"example.bas"', 13, 'Lisp')
        app._call_editor.assert_not_called()

    def test_open_file_uses_focused_repl_line(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        app = Mock()
        app.focus_get.return_value = app.listener_text
        app.basic_repl_mode.get.return_value = True
        app.listener_text.get.side_effect = ['BASIC> LOAD "demo.bas"', 'BASIC> LOAD "demo']
        machine.LispMachine.open_file_at_cursor(app)
        app._open_file_reference.assert_called_once_with('BASIC> LOAD "demo.bas"', 17, 'BBC BASIC')

    def test_editor_focus_keeps_editor_file_navigation(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        app = Mock()
        app.focus_get.return_value = Mock()
        machine.LispMachine.open_file_at_cursor(app)
        app._call_editor.assert_called_once_with('_open_file_at_cursor')
        app._open_file_reference.assert_not_called()

    def test_navigation_opens_file_without_evaluating_input(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.py'
            path.write_text('raise RuntimeError("must not execute")')
            app = Mock()
            source = '"' + str(path) + '"'
            machine.LispMachine._open_file_reference(app, source, len(source), 'Lisp')
            app._open_source_path.assert_called_once_with(str(path))
            app.listener_write.assert_not_called()
