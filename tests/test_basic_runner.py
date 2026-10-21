import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import subprocess


class BasicRunnerTest(TestCase):
    def test_error_maps_numbered_and_selected_source(self):
        from basic_runner import error_source_line
        self.assertEqual(error_source_line('PRINT 1\nFOR', 'BBC syntax error at line 2: expected name', 5), 6)
        self.assertEqual(error_source_line('10 PRINT 1\n100 FOR', 'Error in line 100', 5, numbered=True), 6)
        self.assertIsNone(error_source_line('PRINT 1', 'division by zero'))
        self.assertEqual(error_source_line('PRINT 1\n\nFOR', '? FOR error at line 20', 5, numbered=True), 7)

    def test_python_runner_streams_unsaved_source_and_cleans_temp_file(self):
        from basic_runner import run_python_basic
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)/'mini_basic'
            package.mkdir()
            (package/'__init__.py').write_text('', encoding='utf-8')
            (package/'__main__.py').write_text(
                'import sys, pathlib\np=pathlib.Path(sys.argv[-1])\n'
                'print(p, flush=True)\nprint(p.read_text(encoding="utf-8"), flush=True)\n'
                'sys.stdout.write("\\rprogress\\r");sys.stdout.flush()\n', encoding='utf-8')
            output = []
            result = run_python_basic('PRINT "héllo"', output.append, cwd=folder, package_root=folder)
            self.assertEqual(result, 0)
            text = ''.join(output)
            self.assertIn('PRINT "héllo"', text)
            self.assertIn('\rprogress\r', text)
            self.assertFalse(Path(text.splitlines()[0]).exists())

    def test_cancellation_terminates_child_process(self):
        import basic_runner
        class Cancelled(BaseException):
            pass
        processes = []
        real_popen = subprocess.Popen
        def launch(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            processes.append(child)
            return child
        def cancel(line):
            raise Cancelled()
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)/'mini_basic'
            package.mkdir()
            (package/'__init__.py').write_text('', encoding='utf-8')
            (package/'__main__.py').write_text('import time\nprint("ready", flush=True)\ntime.sleep(60)', encoding='utf-8')
            with patch.object(basic_runner.subprocess, 'Popen', side_effect=launch):
                with self.assertRaises(Cancelled):
                    basic_runner.run_python_basic('PRINT 1', cancel, cwd=folder, package_root=folder)
            self.assertIsNotNone(processes[0].poll())
