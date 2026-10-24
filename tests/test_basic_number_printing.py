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

    def test_strings_and_str_dollar_are_unchanged(self):
        self.mbasic()
        self.assertEqual(self.run_bbc('PRINT "x";STR$(19);"y"'), 'x19y\n')

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
            repl.submit('10 PRINT "A";19;"B"')
            repl.submit('RUN')
            repl.submit('RUN')
        self.assertEqual(output.getvalue(), 'A 19 B\nA 19 B\n')

    def test_editor_basic_run_uses_saved_style(self):
        from test_machine_args import machine
        from test_machine_basic_buffer import _FakeMachine
        app = _FakeMachine('PRINT "A";19;"B"')
        app.tab.name = 'example.bas'
        app.settings = {'basic_number_printing': 'mbasic'}
        machine.LispMachine.eval_buffer(app)
        self.assertIn('A 19 B\n', ''.join(app.lines))
