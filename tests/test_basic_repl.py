import contextlib
import io
import tempfile
from pathlib import Path
from support import LispyTestCase, lispy3 as L


class BasicReplTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        from basic_repl import BasicRepl
        self.repl = BasicRepl(L)
        self.addCleanup(self.repl.close)

    def submit(self, *lines):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            for line in lines: self.repl.submit(line)
        return output.getvalue()

    def test_immediate_state_is_private_and_persistent(self):
        self.assertEqual(self.submit('n=7', 'PRINT ;n'), '7\n')
        self.assertNotIn('n', L.global_env)

    def test_run_uses_current_buffer_until_cli_program_is_edited(self):
        current = ['PRINT "buffer"']
        self.repl.get_current_source = lambda: current[0]
        self.assertEqual(self.submit('RUN'), 'buffer\n')
        current[0] = 'PRINT "edited"'
        self.assertEqual(self.submit('RUN'), 'edited\n')
        self.submit('10 PRINT "stored"')
        current[0] = ''
        self.assertEqual(self.submit('RUN'), 'stored\n')

    def test_cli_rem_program_does_not_run_unrelated_editor_code(self):
        self.repl.get_current_source=lambda: '@ unrelated editor text'
        self.assertEqual(self.submit('10 REMMM THIS IS COMMENT','RUN'), '')

    def test_default_directory_and_relative_load_save(self):
        from basic_repl import BasicRepl
        self.assertEqual(self.repl.directory, Path(__file__).resolve().parents[1]/'basic')
        with tempfile.TemporaryDirectory() as directory:
            session=BasicRepl(L, directory=directory)
            self.addCleanup(session.close)
            session.submit('10 PRINT 42')
            session.submit('SAVE "relative.bas"')
            self.assertEqual((Path(directory)/'relative.bas').read_text(), '10 PRINT 42\n')
            session.submit('NEW')
            session.submit('LOAD "relative.bas"')
            self.assertEqual(session.source(), '10 PRINT 42\n')

    def test_lines_replace_delete_sort_list_and_run(self):
        self.assertEqual(self.submit('30 PRINT "old"', '10 PRINT "first"',
            '20 PRINT "deleted"', '20', '30 PRINT "last"', 'LIST', 'RUN'),
            '10 PRINT "first"\n30 PRINT "last"\nfirst\nlast\n')

    def test_run_resets_variables_but_keeps_program(self):
        self.submit('10 PRINT ;n', 'n=9')
        with self.assertRaisesRegex(Exception, 'Undefined symbol'):
            self.submit('RUN')
        self.assertEqual(self.submit('LIST'), '10 PRINT ;n\n')

    def test_buffer_run_starts_fresh_each_time(self):
        self.repl.get_current_source = lambda: 'PRINT ;n'
        self.submit('n=9')
        for unused in range(2):
            with self.assertRaisesRegex(Exception, 'Undefined symbol'):
                self.submit('RUN')
            self.submit('n=7')

    def test_new_clears_program_and_runtime(self):
        self.submit('10 PRINT 1', 'n=9', 'NEW')
        self.assertEqual(self.submit('LIST'), '')
        with self.assertRaisesRegex(Exception, 'Undefined symbol'):
            self.submit('PRINT ;n')

    def test_load_save_and_failed_load_retains_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'demo file.bas'
            self.submit('10 PRINT "ok"', 'SAVE "'+path.as_posix()+'"', 'NEW',
                        'LOAD "'+path.as_posix()+'"')
            self.assertEqual(self.submit('RUN'), 'ok\n')
            with self.assertRaises(OSError): self.submit('LOAD "'+directory+'/missing.bas"')
            self.assertEqual(self.submit('LIST'), '10 PRINT "ok"\n')

    def test_load_unnumbered_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'demo.bas'; path.write_text('FOR i=1 TO 2\nPRINT ;i\nNEXT\n')
            self.submit('LOAD "'+path.as_posix()+'"')
            self.assertEqual(self.submit('RUN'), '1\n2\n')

    def test_numbered_goto(self):
        self.assertEqual(self.submit('10 IF TRUE THEN 30', '20 PRINT "wrong"',
                                    '30 PRINT "hit"', 'RUN'), 'hit\n')

    def test_compact_numbered_line(self):
        self.assertEqual(self.submit('10PRINT "ok"', 'RUN'), 'ok\n')

    def test_cli_commands(self):
        import subprocess, sys
        result=subprocess.run([sys.executable, 'basic_repl.py'],
            input='10 PRINT "ok"\nRUN\nQUIT\n', capture_output=True, text=True, timeout=15,
            cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ok\n', result.stdout)
        self.assertNotIn('Error:', result.stdout)

    def test_load_comment_header_preserves_explicit_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'demo.bas'
            path.write_text('REM dialect: bbc\n10 IF TRUE THEN 30\n20 PRINT "wrong"\n30 PRINT "hit"\n')
            self.submit('LOAD "'+path.as_posix()+'"')
            self.assertEqual(self.submit('RUN'), 'hit\n')
