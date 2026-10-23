import importlib.util
from pathlib import Path
from unittest import TestCase
from support import REPO_DIR

class StructuredRunnerTest(TestCase):
    def setUp(self):
        path=Path(REPO_DIR)/'basic'/'reference'/'run_structured_checks.py'
        spec=importlib.util.spec_from_file_location('structured_runner',path)
        self.runner=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)

    def test_native_wrapper_only_replaces_terminal_end(self):
        source='10 PRINT "ok"\n20 END\n30 DEF PROCp\n40 ENDPROC\n'
        program=self.runner.instrument(source,Path('folder with spaces/output.txt'))
        self.assertIn('20 OSCLI "SPOOL":QUIT',program)
        self.assertIn('40 ENDPROC',program)
        self.assertIn('SPOOL ""',program)
        self.assertIn('BBC_ERROR:',program)

    def test_documented_difference_is_not_general_error_acceptance(self):
        classify=self.runner.classify
        self.assertEqual(classify('abandoned-for-diagnostic','1\nBBC_ERROR:46:Not in a WHILE loop:90\n','1\n2\ndone\n'),'documented-difference')
        self.assertEqual(classify('exit-for','BBC_ERROR:46:bad:90\n','3\n'),'differs')
        self.assertEqual(classify('abandoned-for-diagnostic','1\nBBC_ERROR:32:bad:90\n','1\n2\ndone\n'),'differs')
