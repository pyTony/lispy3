"""Optional MBASIC numeric PRINT spacing without changing BASIC source."""
import contextlib
import io
from unittest.mock import patch
from test_mini_basic_reader import ReaderTestCase
from support import lispy3 as L


class NumberPrintingTest(ReaderTestCase):
    def setUp(self):
        workspace = L.workspaces.create('number printing regression')
        self.addCleanup(L.workspaces.discard, workspace)
        self.enterContext(L.workspaces.use(workspace))
        super().setUp()

    def mbasic(self):
        self.ev('(bbc-set-print-style! :mbasic)')

    def test_bbc_default_and_switch_back_are_preserved(self):
        source = 'PRINT "A";19;"B"'
        self.assertEqual(self.run_bbc(source), 'A19B\n')
        self.mbasic()
        self.assertEqual(self.run_bbc(source), 'A 19 B\n')
        self.ev('(bbc-set-print-style! :bbc)')
        self.assertEqual(self.run_bbc(source), 'A19B\n')

    def test_old_star_trek_orders_need_no_print_edits(self):
        self.mbasic()
        source = 'K9=19:T0=2400:T9=28\n1240 PRINT"     DESTROY THE";K9;"KLINGON WARSHIPS WHICH HAVE INVADED"\n1260 PRINT"   ON STARDATE";T0+T9;"  THIS GIVES YOU";T9;"DAYS."'
        self.assertEqual(self.run_bbc(source), '     DESTROY THE 19 KLINGON WARSHIPS WHICH HAVE INVADED\n   ON STARDATE 2428   THIS GIVES YOU 28 DAYS.\n')

    def test_sign_zero_fraction_and_consecutive_numbers(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('PRINT -2;0;1.5'), '-2  0  1.5 \n')
        self.assertEqual(self.run_bbc('PRINT 1;2;'), ' 1  2 ')

    def test_strings_unchanged_and_str_dollar_keeps_the_sign_space(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('PRINT "x";STR$(19);"y";STR$(-2)'), 'x 19y-2\n')

    def test_cursor_columns_include_numeric_padding(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('PRINT 7;\nPRINT TAB(6);"X"'), ' 7    X\n')

    def test_invalid_mode_reports_clear_error(self):
        with self.assertRaisesRegex(Exception, 'print.*style|printing'):
            self.ev('(bbc-set-print-style! :other)')

    def test_repl_applies_style_after_run_resets_workspace(self):
        from lispy_support.basic_repl import BasicRepl
        repl = BasicRepl(L, print_style='mbasic')
        self.addCleanup(repl.close)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            repl.submit('10 a=19:print "A";A;"B"')
            repl.submit('RUN')
            repl.submit('NEW')
            repl.submit('10 a=19:print "A";A;"B"')
            repl.submit('RUN')
        self.assertEqual(output.getvalue(), 'A 19 B\nA 19 B\n')

    def test_editor_basic_run_uses_saved_style(self):
        from test_machine_args import machine
        from test_machine_basic_buffer import _FakeMachine
        app = _FakeMachine('a=19:print "A";A;"B"')
        app.tab.name = 'example.bas'
        app.settings = {'basic_number_printing': 'mbasic'}
        machine.LispMachine.eval_buffer(app)
        self.assertIn('A 19 B\n', ''.join(app.lines))

    def test_run_as_mbasic_is_one_off(self):
        from test_machine_args import machine
        from test_machine_basic_buffer import _FakeMachine
        app = _FakeMachine('A=19:PRINT "A";A;"B"')
        app.tab.name = 'example.bas'
        app.settings = {'basic_number_printing': 'bbc'}
        app.eval_buffer = lambda **kwargs: machine.LispMachine.eval_buffer(app, **kwargs)
        machine.LispMachine.eval_basic_buffer_as(app, backend='lispy', print_style='mbasic')
        self.assertIn('A 19 B\n', ''.join(app.lines))
        self.assertEqual(app.settings, {'basic_number_printing': 'bbc'})
        app.lines.clear()
        machine.LispMachine.eval_buffer(app)
        self.assertIn('A19B\n', ''.join(app.lines))

    def test_editor_terminal_buffer_uses_saved_style(self):
        from unittest.mock import Mock
        from test_machine_args import machine
        from test_machine_basic_buffer import _FakeMachine
        app = _FakeMachine('a=19:print "A";A;"B"')
        app.settings = {'basic_number_printing': 'mbasic'}
        app.basic_output = Mock()
        app.basic_output.get.return_value = 'ansi'
        terminal = io.StringIO()
        @contextlib.contextmanager
        def output():
            with contextlib.redirect_stdout(terminal), patch.object(machine.lispy_terminal, 'terminal_output_active', return_value=True):
                yield
        with patch.object(machine.lispy_terminal, 'ansi_terminal_output', output):
            machine.LispMachine.eval_buffer(app, basic=True)
        self.assertEqual(terminal.getvalue(), 'A 19 B\n')

    def test_gui_choice_updates_session_and_persisted_setting(self):
        from types import SimpleNamespace
        from test_machine_args import machine
        app = SimpleNamespace(settings={}, basic_repl=SimpleNamespace(print_style='bbc'))
        with patch.object(machine, 'save_settings') as save:
            machine.LispMachine._set_basic_number_printing(app, 'MBASIC')
        self.assertEqual(app.settings['basic_number_printing'], 'mbasic')
        self.assertEqual(app.basic_repl.print_style, 'mbasic')
        save.assert_called_once_with(app.settings)

    def test_standalone_repl_flag(self):
        import subprocess
        import sys
        from support import REPO_DIR
        result = subprocess.run([sys.executable, '-m', 'lispy_support.basic_repl', '--print-style', 'mbasic'], input='a=19:print "A";A;"B"\nQUIT\n', cwd=REPO_DIR, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('A 19 B\n', result.stdout)

    def test_mbasic_same_option_accepts_lowercase_keywords_and_names(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('A=1:print a'), ' 1 \n')

    def test_mbasic_preserves_strings_and_unquoted_data(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('data MixedCase,print\nread a$,B$\nprint A$;"/";b$;"/MiXeD"'), 'MixedCase/print/MiXeD\n')

    def test_mbasic_arrays_loops_and_functions(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('dim Values(2)\nfor I=1 to 2\nvalues(i)=I\nnext i\ndef FNdouble(N)=n*2\nprint fnDOUBLE(VALUES(2))'), ' 4 \n')

    def test_bbc_option_restores_case_sensitive_variables(self):
        self.mbasic()
        self.ev('(bbc-set-print-style! :bbc)')
        self.assertEqual(self.run_bbc('a=2:A=1:PRINT a;A'), '         21\n')

    def test_mbasic_procedure_and_local_names(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('procHello(3)\nend\ndef PROCheLLo(Value)\nlocal Tmp\ntMP=value+1\nprint tmp\nendproc'), ' 4 \n')

    def test_mbasic_comments_and_lowercase_exponent(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('remMixedCase @ ignored\nprint 1e2'), ' 100 \n')
