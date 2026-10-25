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
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 1:MOVE 0,0:DRAW 12,0:GCOL 2:PLOT 69,8,8')
            self.assertEqual(self.pixel(0,255), [255,0,0])
            self.assertEqual(self.pixel(3,255), [255,0,0])
            self.assertEqual(self.pixel(2,253), [0,255,0])
            self.basic('ORIGIN 4,4:GCOL 4:PLOT 0,0')
            self.assertEqual(self.pixel(1,254), [0,0,255])

    def test_background_clear_and_mode_reset(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
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
                                ('PLOT 77,0,0','unsupported PLOT')]:
            with self.subTest(source=source), self.assertRaisesRegex(Exception,message):
                self.basic(source)
            self.assertEqual(self.ev('(graphics-mode-info)'), [9,320,256,16,1280,1024])

    def test_arity_diagnostics(self):
        for source in ['MOVE 1','DRAW 1,2,3','GCOL 1,2,3','PLOT 1','ORIGIN 1','CLG 1']:
            with self.subTest(source=source), self.assertRaises(Exception):
                self.basic(source)

    def test_drawing_function_is_not_automatically_memoized(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
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
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic(source)
        self.assertEqual(self.pixel(0,131), [0,255,0])
        self.assertEqual(self.pixel(160,131), [0,0,0])
        self.assertEqual(self.pixel(0,132), [0,0,0])
        self.assertNotEqual(self.pixel(0,126), [0,0,0])

    def test_origin_change_preserves_existing_physical_cursor(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 1:MOVE 0,0:ORIGIN 4,0:DRAW 4,0')
        self.assertEqual(self.pixel(0,255), [255,0,0])
        self.assertEqual(self.pixel(1,255), [255,0,0])
        self.assertEqual(self.pixel(2,255), [255,0,0])

    def test_off_and_on_hide_and_show_cursor_without_error(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic('MODE 9 : OFF\nGCOL 1:PLOT 0,0:ON')
        self.assertEqual(self.pixel(0,255), [255,0,0])

    def test_unknown_statement_is_named_instead_of_asking_for_equals(self):
        with self.assertRaisesRegex(Exception, 'unknown statement FOO'):
            self.basic('FOO')
        with self.assertRaisesRegex(Exception, 'expected = after the variable X'):
            self.basic('X 5')

    def test_plot_85_fills_triangle_from_last_two_points(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic('MODE 9:GCOL 2:MOVE 0,0:MOVE 400,0:PLOT 85,0,400')
        self.assertEqual(self.pixel(1,254), [0,255,0])
        self.assertEqual(self.pixel(90,254), [0,255,0])
        self.assertEqual(self.pixel(98,254), [0,0,0])
        self.assertEqual(self.pixel(90,170), [0,0,0])

    def test_closing_the_window_ends_an_endless_basic_program(self):
        from lispy_support.lispy_graphics import Graphics
        original, frames = Graphics.clear, []

        def clear(g, color=None):
            original(g, color)
            frames.append(1)
            if len(frames) == 3:
                g.closed_by_user = True     # as present() does on the close box
        with patch('lispy_support.lispy_graphics.Graphics.open'), \
             patch('lispy_support.lispy_graphics.Graphics.clear', clear):
            self.basic('MODE 9\nREPEAT\nCLS\nPRINT "frame"\nUNTIL FALSE\nPRINT "after"')
        self.assertEqual(len(frames), 3)
        # A Lisp program keeps its own loop test: drawing goes on headless.
        self.ev('(graphics-mode 9)')
        self.ev('(graphics-pixel 0 0)')


class LispGraphicsPrimitivesTest(LispyTestCase):
    def pixel(self, x, y):
        return self.ev(f'(graphics-get-pixel {x} {y})')

    def setUp(self):
        super().setUp()
        self.ev('(graphics-rgb-mode 40 30)')

    def test_fills_rectangle_triangle_polygon_and_circle(self):
        self.ev('(graphics-fill-rect 1 1 3 2 9 9 9)')
        self.assertEqual(self.pixel(3,2), [9,9,9])
        self.assertEqual(self.pixel(4,2), [0,0,0])
        self.ev('(graphics-triangle 10 0 20 0 10 10 1 2 3)')
        self.assertEqual(self.pixel(11,1), [1,2,3])
        self.assertEqual(self.pixel(19,9), [0,0,0])
        self.ev('(graphics-polygon (list 30 0 39 0 39 9 30 9) 4 5 6)')
        self.assertEqual(self.pixel(38,8), [4,5,6])
        self.assertEqual(self.pixel(39,9), [0,0,0])
        self.ev('(graphics-circle-fill 10 20 5 7 7 7)')
        self.assertEqual(self.pixel(10,20), [7,7,7])
        self.assertEqual(self.pixel(14,20), [7,7,7])
        self.assertEqual(self.pixel(14,24), [0,0,0])

    def test_lines_draws_polyline_in_one_call_clipped(self):
        self.ev("(graphics-lines '((0 0) (5 0) (5 5) (60 5)) 255 0 0)")
        for x, y in ((0,0), (5,0), (5,3), (39,5)):
            self.assertEqual(self.pixel(x,y), [255,0,0])
        self.assertEqual(self.pixel(4,1), [0,0,0])

    def test_lines_match_the_reference_bresenham(self):
        from lispy_support.lispy_graphics import Graphics
        from lispy_support.graphics_modes import GraphicsMode
        mode = GraphicsMode(-1, 40, 30, 1, ((0, 0, 0),), 40, 30)
        fast = Graphics(mode)
        segments = ((0,4,39,15), (39,29,0,0), (3,25,30,2), (7,0,7,29), (2,2,2,2), (30,9,5,9))
        for segment in segments:
            fast.line(*segment, (255, 255, 255))
        expected = Graphics(mode)
        for x0, y0, x1, y1 in segments:
            dx, dy = abs(x1-x0), -abs(y1-y0)
            sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
            err = dx + dy
            while True:
                expected.pixel(x0, y0)
                if (x0, y0) == (x1, y1):
                    break
                e2 = 2*err
                if e2 >= dy:
                    err += dy; x0 += sx
                if e2 <= dx:
                    err += dx; y0 += sy
        self.assertEqual(fast.pixels, expected.pixels)

    def test_manual_refresh_shows_only_handed_over_frames(self):
        from lispy_support.lispy_graphics import Graphics
        from lispy_support.graphics_modes import GraphicsMode
        g = Graphics(GraphicsMode(-1, 4, 4, 1, ((0, 0, 0),), 4, 4))
        g.set_auto_refresh(False)
        g.pixel(0, 0)
        self.assertEqual(g._frame[:3], bytes(3))
        g.refresh()
        self.assertEqual(g._frame[:3], bytes((255, 255, 255)))
        self.ev('(graphics-refresh #f)')
        self.ev('(graphics-pixel 0 0)')
        self.ev('(graphics-refresh)')
        self.ev('(graphics-refresh #t)')

    def test_drawing_does_not_go_through_the_window_dispatcher(self):
        from lispy_support import lispy_graphics_bindings as B
        calls = []
        B.set_dispatcher(lambda fn, *args: calls.append(fn) or fn(*args))
        try:
            self.ev('(graphics-line 0 0 5 5)')
            self.ev('(graphics-triangle 0 0 5 0 0 5)')
            self.ev('(graphics-window-open?)')
        finally:
            B.set_dispatcher(None)
        self.assertEqual(len(calls), 1)


class BasicPaletteTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        L.load_workspace('mini-basic')

    basic = BasicGraphicsTest.basic
    pixel = BasicGraphicsTest.pixel

    def test_colour_n_rgb_sets_the_logical_colour_for_drawing(self):
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic('MODE 8:COLOUR 1,10,20,30:GCOL 0,1:PLOT 0,0')
            self.assertEqual(self.ev('(graphics-mode-info)'), [8,640,512,16,1280,1024])
            self.assertEqual(self.pixel(0,511), [10,20,30])
            self.basic('MODE 8:GCOL 1:PLOT 0,0')
            self.assertEqual(self.pixel(0,511), [255,0,0])
        with self.assertRaisesRegex(Exception, 'COLOUR takes n or n,r,g,b'):
            self.basic('COLOUR 1,2')

    def test_random_shapes_example_runs(self):
        from pathlib import Path
        from support import REPO_DIR
        source=(Path(REPO_DIR)/'basic/graphics/random-shapes.bas').read_text().replace('count%=300','count%=5')
        with patch('lispy_support.lispy_graphics.Graphics.open'):
            self.basic(source)
        self.assertEqual(self.ev('(graphics-mode-info)')[0], 8)
