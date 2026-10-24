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
        self.assertIn('Name: Hello Ada\n', ''.join(output))

    def test_python_reindent_normalizes_block_width_without_changing_strings(self):
        from lispy_support.editor_tools import indent_python
        source = 'if True:\n  text = """first\n  literal content\n"""\n  print(text)\n'
        expected = 'if True:\n    text = """first\n  literal content\n"""\n    print(text)\n'
        self.assertEqual(indent_python(source), expected)
        self.assertEqual(indent_python(expected), expected)
