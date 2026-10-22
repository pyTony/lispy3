"""BASIC output shares VDU state; failed calls restore dynamic bindings."""
from support import lispy3
from test_mini_basic_reader import ReaderTestCase


class OutputStreamTest(ReaderTestCase):
    def test_print_colour_matches_vdu_and_keeps_columns(self):
        self.assertEqual(self.run_bbc(
            'PRINT "a";CHR$(17);CHR$(1);TAB(3);"b"'),
            'a\x1b[31m  b\n')

    def test_print_and_vdu_complete_each_others_parameters(self):
        self.assertEqual(self.run_bbc(
            'VDU 17:PRINT CHR$(132);"x";CHR$(31);:VDU 3,1:PRINT "y"'),
            '\x1b[44mx\x1b[2;4Hy\n')

    def test_print_clear_and_home_consume_no_columns(self):
        self.assertEqual(self.run_bbc(
            'PRINT "old";CHR$(12);TAB(2);"x";CHR$(30);TAB(1);"y"'),
            'old\x1b[2J\x1b[H  x\x1b[H y\n')

    def test_unicode_printing_and_high_byte_parameters(self):
        self.assertEqual(self.run_bbc('PRINT "Hyvää päivää — λ"'),
                         'Hyvää päivää — λ\n')
        self.assertEqual(self.run_bbc('PRINT CHR$(17);CHR$(129);"ä"'),
                         '\x1b[41mä\n')

    def test_print_rejects_unsupported_vdu_and_recovers(self):
        with self.assertRaisesRegex(Exception, 'VDU: unsupported control 22'):
            self.run_bbc('PRINT CHR$(22);')
        self.assertEqual(self.run_bbc('PRINT "ok"'), 'ok\n')

    def test_print_newline_can_complete_a_pending_parameter(self):
        # PRINT's implicit CR/LF is output too, not an out-of-band operation.
        self.assertEqual(self.run_bbc('VDU 17:PRINT'), '\x1b[95m\x1b[1B')

    def test_raw_ansi_bypasses_pending_vdu(self):
        self.assertEqual(self.run_bbc('VDU 17:ANSI 27,"[0m":VDU 1,88'),
                         '\x1b[0m\x1b[31mX')


class DynamicCleanupTest(ReaderTestCase):
    def test_proc_restores_parameter_and_local_after_error(self):
        with self.assertRaisesRegex(Exception, 'Out of DATA'):
            self.run_bbc('x=11:y=22:PROCbad(3):END\n'
                         'DEF PROCbad(x)\nLOCAL y\ny=9:READ y\nENDPROC')
        self.assertEqual(self.ev('x'), 11)
        self.assertEqual(self.ev('y'), 22)

    def test_nested_calls_restore_outer_bindings_and_gosub_state(self):
        with self.assertRaisesRegex(Exception, 'Out of DATA'):
            self.run_bbc('x=11:PROCouter(3):END\n'
                         'DEF PROCouter(x)\nPROCinner(4)\nENDPROC\n'
                         'DEF PROCinner(x)\nGOSUB 100\n'
                         '100 READ x:RETURN\nENDPROC')
        self.assertEqual(self.ev('x'), 11)
        self.assertEqual(self.ev('bbc-gosub-depth'), 0)
        self.assertEqual(self.ev('(length bbc-gosub-handlers)'), 0)
        self.assertEqual(self.run_bbc('PRINT "again"'), 'again\n')

    def test_end_in_proc_restores_locals(self):
        self.assertEqual(self.run_bbc('x=11:PROCstop(3):PRINT "wrong":END\n'
                                     'DEF PROCstop(x)\nEND\nENDPROC'), '')
        self.assertEqual(self.ev('x'), 11)

    def test_fn_restores_parameter_after_runtime_error(self):
        with self.assertRaisesRegex(Exception, 'division by zero'):
            self.run_bbc('x=11:PRINT FNbad(3):END\nDEF FNbad(x)=1/0')
        self.assertEqual(self.ev('x'), 11)

    def test_base_macros_restore_without_extension_override(self):
        # Loading the base source up to the extension load exercises its own bbc-def.
        from pathlib import Path
        source = (Path(lispy3.__file__).parent/'lisp'/'mini-basic.lisp').read_text()
        self.ev('(begin '+source.rsplit('(load "mini-basic-ext")', 1)[0]+'\n)')
        self.ev('(define x 11)')
        self.ev('(DEF-PROC (bad x) (LET x 9) (/ 1 0))')
        with self.assertRaisesRegex(Exception, 'division by zero'):
            self.ev('(PROC bad 3)')
        self.assertEqual(self.ev('x'), 11)
