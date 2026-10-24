"""Python execution and conservative editor indentation regressions."""
import tempfile
from unittest import TestCase


class PythonEditorTest(TestCase):
    def test_python_program_reads_input_and_runs_unsaved_source(self):
        from lispy_support.basic_runner import run_python_source
        with tempfile.TemporaryDirectory() as folder:
            output = []
            status = run_python_source('name=input("Name: ")\nprint("Hello", name)',
                output.append, cwd=folder, read_input=lambda: 'Ada')
        self.assertEqual(status, 0)
        self.assertIn('Name: Hello Ada\n', ''.join(output).replace('\r\n','\n'))

    def test_python_input_is_not_evaluated_and_eof_is_reported(self):
        from lispy_support.basic_runner import run_python_source
        with tempfile.TemporaryDirectory() as folder:
            output = []
            self.assertEqual(run_python_source('print(input())', output.append,
                cwd=folder, read_input=lambda: '1+2'), 0)
            self.assertEqual(''.join(output).strip(), '1+2')
            output.clear()
            self.assertNotEqual(run_python_source('input("Value: ")', output.append,
                cwd=folder), 0)
            self.assertIn('EOFError', ''.join(output))

    def test_python_input_cancellation_reaps_the_child(self):
        from lispy_support import basic_runner
        from unittest.mock import patch
        import subprocess
        class Cancelled(BaseException):
            pass
        children = []
        popen = subprocess.Popen
        def launch(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            return child
        def cancel():
            raise Cancelled()
        with tempfile.TemporaryDirectory() as folder, patch.object(basic_runner.subprocess, 'Popen', side_effect=launch):
            with self.assertRaises(Cancelled):
                basic_runner.run_python_source('input()', lambda text: None,
                    cwd=folder, read_input=cancel)
        self.assertIsNotNone(children[0].poll())

    def test_python_reindent_preserves_nested_suites_and_selection(self):
        from lispy_support.editor_tools import indent_python
        source = 'def f():\n\tif True:\n\t\treturn 1\n\telse:\n\t\treturn 2\n'
        expected = 'def f():\n    if True:\n        return 1\n    else:\n        return 2\n'
        self.assertEqual(indent_python(source), expected)
        self.assertEqual(indent_python(expected, first_line=1, stop_line=3), expected)
        with self.assertRaises(SyntaxError):
            indent_python('if True:\nprint(1)\n')

    def test_python_return_indentation(self):
        from lispy_support.editor_tools import next_python_indent
        for source, expected in [('if True:', 4), ('    if True: # header', 8),
                ('values = [', 4), ('values = [\n    1,', 4),
                ('\tif True:', 12), ('    print("colon:")', 4),
                ('    text = """literal:\n    more:', 4)]:
            with self.subTest(source=source):
                self.assertEqual(next_python_indent(source), expected)

    def test_python_reindent_normalizes_block_width_without_changing_strings(self):
        from lispy_support.editor_tools import indent_python
        source = 'if True:\n  text = """first\n  literal content\n"""\n  print(text)\n'
        expected = 'if True:\n    text = """first\n  literal content\n"""\n    print(text)\n'
        self.assertEqual(indent_python(source), expected)
        self.assertEqual(indent_python(expected), expected)
