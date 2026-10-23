"""Graphics command regressions; no display or pygame needed for pixel checks."""
from unittest.mock import patch
from support import LispyTestCase, lispy3 as L


class BasicGraphicsTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        L.load_workspace('mini-basic')

    def basic(self, source):
        return self.ev('(bbc-run '+L.lisp_str(L.String(source))+')')

    def pixel(self, x, y):
        return self.ev(f'(graphics-get-pixel {x} {y})')

    def test_mode_dimensions_and_lisp_headless_drawing(self):
        self.ev('(graphics-mode 9)')
        self.assertEqual(self.ev('(graphics-mode-info)'), [9,320,256,16,1280,1024])
        self.ev('(graphics-pixel 4 6 10 20 30)')
        self.assertEqual(self.pixel(4,6), [10,20,30])
        self.assertFalse(self.ev('(graphics-window-open?)'))

    def test_basic_move_draw_point_and_origin(self):
        with patch('lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 1:MOVE 0,0:DRAW 12,0:GCOL 2:PLOT 69,8,8')
            self.assertEqual(self.pixel(0,255), [255,0,0])
            self.assertEqual(self.pixel(3,255), [255,0,0])
            self.assertEqual(self.pixel(2,253), [0,255,0])
            self.basic('ORIGIN 4,4:GCOL 4:PLOT 0,0')
            self.assertEqual(self.pixel(1,254), [0,0,255])

    def test_background_clear_and_mode_reset(self):
        with patch('lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 130:CLG')
            self.assertEqual(self.pixel(0,0), [0,255,0])
            self.basic('MODE 1')
            self.assertEqual(self.pixel(0,0), [0,0,0])
            self.basic('DRAW 0,0')
            self.assertEqual(self.pixel(0,255), [255,255,255])

    def test_invalid_commands_fail_without_corrupting_surface(self):
        self.ev('(graphics-mode 9)')
        for source, message in [('MODE 999','unsupported graphics MODE'),
                                ('GCOL 3,1','GCOL drawing action'),
                                ('PLOT 85,0,0','unsupported PLOT')]:
            with self.subTest(source=source), self.assertRaisesRegex(Exception,message):
                self.basic(source)
            self.assertEqual(self.ev('(graphics-mode-info)'), [9,320,256,16,1280,1024])

    def test_arity_diagnostics(self):
        for source in ['MOVE 1','DRAW 1,2,3','GCOL 1,2,3','PLOT 1','ORIGIN 1','CLG 1']:
            with self.subTest(source=source), self.assertRaises(Exception):
                self.basic(source)

    def test_drawing_function_is_not_automatically_memoized(self):
        with patch('lispy_graphics.Graphics.open'):
            self.basic('MODE 9\nDEF FNdot(x)\nPLOT 69,x,0\n=1\n')
            self.basic('a=FNdot(0):CLG:a=FNdot(0)')
            self.assertEqual(self.pixel(0,255), [255,255,255])

    def test_separate_environments_have_separate_framebuffers(self):
        self.ev('(graphics-mode 9)')
        self.ev('(graphics-pixel 0 0 255 0 0)')
        other=L.standard_env()
        L.eval_exp(L.parse('(graphics-mode 9)'),other)
        self.assertEqual(L.eval_exp(L.parse('(graphics-get-pixel 0 0)'),other), [0,0,0])
        self.assertEqual(self.pixel(0,0), [255,0,0])

    def test_six_row_mandelbrot_basic_file(self):
        from pathlib import Path
        from support import REPO_DIR
        source=(Path(REPO_DIR)/'basic/graphics/mandelbrot-preview.bas').read_text()
        with patch('lispy_graphics.Graphics.open'):
            self.basic(source)
        self.assertEqual(self.pixel(0,131), [0,255,0])
        self.assertEqual(self.pixel(160,131), [0,0,0])
        self.assertEqual(self.pixel(0,132), [0,0,0])
        self.assertNotEqual(self.pixel(0,126), [0,0,0])

    def test_origin_change_preserves_existing_physical_cursor(self):
        with patch('lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 1:MOVE 0,0:ORIGIN 4,0:DRAW 4,0')
        self.assertEqual(self.pixel(0,255), [255,0,0])
        self.assertEqual(self.pixel(1,255), [255,0,0])
        self.assertEqual(self.pixel(2,255), [255,0,0])
