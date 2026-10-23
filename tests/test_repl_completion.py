import tempfile
from pathlib import Path
from unittest import TestCase


class FilenameCompletionTest(TestCase):
    def test_basic_paths_with_spaces_and_directory_suffix(self):
        from repl_completion import filename_completion
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'demo file.bas').touch(); (root/'demos').mkdir()
            start, matches=filename_completion('LOAD "dem', basic=True, cwd=root)
            self.assertEqual(start, 6)
            self.assertEqual(matches, ['demo file.bas', 'demos/'])

    def test_lisp_paths_and_non_filename_context(self):
        from repl_completion import filename_completion
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'demo.lisp').touch()
            self.assertEqual(filename_completion('(load "de', cwd=directory), (7, ['demo.lisp']))
            self.assertIsNone(filename_completion('(display "de', cwd=directory))
            self.assertIsNone(filename_completion('PRINT "de', basic=True, cwd=directory))

    def test_closed_filename_is_not_completed(self):
        from repl_completion import filename_completion
        self.assertIsNone(filename_completion('LOAD "demo.bas"', basic=True))
