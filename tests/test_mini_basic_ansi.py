"""ANSI syntactic sugar emits control bytes without consuming print columns."""
import contextlib
import io
from test_mini_basic_reader import ReaderTestCase


class AnsiTerminalTest(ReaderTestCase):
    def test_cls_clears_homes_and_resets_column(self):
        self.assertEqual(self.run_bbc('PRINT "old";:CLS:PRINT TAB(2);"x"'),
                         'old\x1b[2J\x1b[H  x\n')

    def test_colour_foreground_background_and_bright(self):
        self.assertEqual(self.run_bbc('COLOUR 1:COLOUR 132:COLOR 15:COLOUR 136'),
                         '\x1b[31m\x1b[44m\x1b[97m\x1b[100m')

    def test_colour_does_not_consume_columns(self):
        self.assertEqual(self.run_bbc('PRINT "a";:COLOUR 2:PRINT TAB(3);"b"'),
                         'a\x1b[32m  b\n')

    def test_tab_xy_uses_zero_based_column_and_row(self):
        self.assertEqual(self.run_bbc('PRINT TAB(4,2);"x";TAB(7);"y"'),
                         '\x1b[3;5Hx  y\n')

    def test_bad_colour_and_coordinates_raise(self):
        for source in ('COLOUR -1', 'COLOUR 16', 'COLOUR 144', 'PRINT TAB(-1,0)', 'PRINT TAB(0,-1)'):
            with self.subTest(source=source), self.assertRaisesRegex(Exception, 'COLOUR|TAB'):
                self.run_bbc(source)

    def test_lisp_macros_share_the_terminal_helpers(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-program (CLS) (COLOUR 1) (COLOR 130) (PRINT (TAB 0 0) "ok") (ANSI-RESET))')
        self.assertEqual(out.getvalue(), '\x1b[2J\x1b[H\x1b[31m\x1b[42m\x1b[1;1Hok\n\x1b[0m')

    def test_vdu_byte_stream_controls_and_text(self):
        self.assertEqual(self.run_bbc('VDU 12,17,1,31,4,2,65,13,10,30'),
                         '\x1b[2J\x1b[H\x1b[31m\x1b[3;5HA\r\x1b[1B\x1b[H')

    def test_vdu_parameters_can_span_statements(self):
        self.assertEqual(self.run_bbc('VDU 17:VDU 2:VDU 31,3:VDU 1,88'),
                         '\x1b[32m\x1b[2;4HX')

    def test_vdu_lisp_macro_accepts_byte_expressions(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-program (VDU 17 (+ 128 4) 31 0 0 65))')
        self.assertEqual(out.getvalue(), '\x1b[44m\x1b[1;1HA')

    def test_vdu_unsupported_control_is_clear_and_recovers(self):
        with self.assertRaisesRegex(Exception, 'VDU: unsupported control 22'):
            self.run_bbc('VDU 22')
        self.assertEqual(self.run_bbc('VDU 65'), 'A')

    def test_terminal_effects_in_fn_are_not_memoized(self):
        self.assertEqual(self.run_bbc('DEF FNclear(n)\nCLS\n=n\nPRINT ;FNclear(1);FNclear(1)'),
                         '\x1b[2J\x1b[H1\x1b[2J\x1b[H1\n')

    def test_vdu_down_preserves_column_and_escape_is_not_raw_ansi(self):
        self.assertEqual(self.run_bbc('PRINT "ab";:VDU 10:PRINT TAB(4);"x"'),
                         'ab\x1b[1B  x\n')
        with self.assertRaisesRegex(Exception, 'VDU: unsupported control 27'):
            self.run_bbc('VDU 27')

    def test_vdu_bytes_wrap_and_do_not_leak_parameter_after_error(self):
        self.assertEqual(self.run_bbc('VDU 321'), 'A')
        with self.assertRaisesRegex(Exception, 'COLOUR'):
            self.run_bbc('VDU 17,16')
        self.assertEqual(self.run_bbc('VDU 65'), 'A')

    def test_ansi_is_raw_and_distinct_from_vdu(self):
        self.assertEqual(self.run_bbc('ANSI 27,91,51,49,109:PRINT "red";:ANSI 27,"[0m"'),
                         '\x1b[31mred\x1b[0m')
        self.assertEqual(self.run_bbc('ANSI 17,1'), '\x11\x01')

    def test_ansi_macro_and_print_columns(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-program (PRINT "a" :semi) (ANSI 27 "[31m") (PRINT (TAB 3) "b") (ANSI-RESET))')
        self.assertEqual(out.getvalue(), 'a\x1b[31m  b\n\x1b[0m')
