"""The soccer ball FPS test in BBC BASIC and native Lispy; no display needed."""
import tempfile
from pathlib import Path
from unittest.mock import patch
from support import LispyTestCase, REPO_DIR, lispy3 as L
from lispy_support import lispy_graphics as G


class SoccerBallTest(LispyTestCase):
    def capture(self):
        made = []
        original = G.Graphics.__init__
        def init(graphics, *args, **kwargs):
            original(graphics, *args, **kwargs)
            made.append(graphics)
        return made, patch.object(G.Graphics, '__init__', init)

    def test_basic_original_draws_ball_and_black_pentagons(self):
        L.load_workspace('mini-basic')
        source = (Path(REPO_DIR)/'basic/graphics/soccerball.bas').read_text()
        source = source.replace('UNTIL FALSE', 'UNTIL c > 0.1').replace('WAIT 1', 'WAIT 0')
        made, init = self.capture()
        with init, patch.object(G.Graphics, 'open'):
            self.ev('(bbc-run '+L.lisp_str(L.String(source))+')')
        g = made[-1]
        self.assertFalse(g.auto_refresh)
        frame = g._frame
        colours = {bytes(frame[i:i+3]) for i in range(0, len(frame), 3)}
        self.assertEqual(colours, {bytes((0, 255, 0)), bytes((255, 255, 0)), bytes((0, 0, 0))})
        self.assertEqual(g.get_pixel(0, 0), (0, 255, 0))       # COLOUR 130 + CLS
        self.assertEqual(g.get_pixel(160, 30), (255, 255, 0))   # GCOL 3 : CIRCLE FILL

    def test_native_lispy_version_counts_frames(self):
        source = (Path(REPO_DIR)/'lisp/programs/soccer-ball.lisp').read_text()
        source = source.replace('(define frames 300)', '(define frames 3)')
        made, init = self.capture()
        with init, patch.object(G.Graphics, 'open', lambda g, *a: g), \
                patch.object(G.Graphics, 'window_open', True), \
                patch.object(G.Graphics, 'present', lambda g: []):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'soccer-ball.lisp'
                path.write_text(source)
                self.ev('(load '+L.lisp_str(L.String(str(path)))+')')
        self.assertEqual(self.ev('frame'), 3)
        g = made[-1]
        self.assertEqual(g.get_pixel(0, 0), (0, 128, 0))
        self.assertEqual(g.get_pixel(320, 256 - 210), (255, 255, 255))
        self.assertIn((0, 0, 0), {g.get_pixel(x, 256) for x in range(120, 520)})


class MatrixProductTest(LispyTestCase):
    def test_mat_star_shapes_and_in_place_result(self):
        self.assertEqual(self.ev('(mat* [[1 2] [3 4]] [[5 6] [7 8]])'), [[19, 22], [43, 50]])
        self.assertEqual(self.ev('(mat* [1 2] [[5 6] [7 8]])'), [19, 22])
        self.assertEqual(self.ev('(mat* [[1 2] [3 4]] [1 1])'), [3, 7])
        self.assertEqual(self.ev('(let [m [[1 0] [0 1]]] (mat* [[2 0] [0 2]] m m) m)'), [[2, 0], [0, 2]])
        with self.assertRaisesRegex(Exception, 'cannot multiply'):
            self.ev('(mat* [[1 2]] [[1 2]])')


class BasicArrayStatementsTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        L.load_workspace('mini-basic')

    def run_basic(self, source):
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.ev('(bbc-run '+L.lisp_str(L.String(source))+')')
        return out.getvalue().split()

    def test_whole_array_assignment_matrix_product_and_sum(self):
        self.assertEqual(self.run_basic(
            'DIM b(2,2), c(2,2), v(1,3)\nb = 7\n'
            'b() = 1,2,3,4,5,6,7,8,9 : c() = 1 : c() = b() . c()\n'
            'PRINT c(0,0); " "; c(2,2); " "; b\n'
            'v() = 0,1,2,3, 4,5,6,7 : PRINT SUM(v()); " "; SUM(v(1, 1 TO 3))\n'
            'c() = b() * 2 : PRINT c(1,1)\n'), ['6', '24', '7', '28', '18', '10'])

    def test_data_items_are_expressions_for_numeric_read(self):
        self.assertEqual(self.run_basic(
            's = 2 : t = s*3\nREAD x, y, z, w$, v$\nPRINT x; " "; y; " "; z; " "; w$; " "; v$\n'
            'DATA t, -s, 2*t, -s, apple\n'), ['6', '-2', '12', '-s', 'apple'])

    def test_keyword_followed_by_digits_and_star_refresh(self):
        self.assertEqual(self.run_basic('X = SQR4 : A5 = 3\n*REFRESH OFF\nWAIT 0\nPRINT X; " "; A5\n'),
                         ['2', '3'])
