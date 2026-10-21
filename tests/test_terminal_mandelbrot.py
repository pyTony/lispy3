"""Terminal Mandelbrot examples agree across BASIC/Lisp and plain/ANSI output."""
import contextlib
import io
import re
from pathlib import Path
from support import LispyTestCase, lispy3, REPO_DIR

ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
PROGRAMS = Path(REPO_DIR)/'lisp'/'programs'


class TerminalMandelbrotTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        self.macros = lispy3.macro_table.copy()
        lispy3.library_system.reset()
        lispy3.macro_table.clear()
        self.addCleanup(self.restore_macros)

    def restore_macros(self):
        lispy3.macro_table.clear()
        lispy3.macro_table.update(self.macros)

    def capture(self, source):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev(source)
        return out.getvalue()

    def load_renderers(self):
        lispy3.load_workspace(str(PROGRAMS/'mandelbrot-terminal-lib.lisp'))
        self.ev('(import (only mini-basic bbc-load bbc-run))')
        self.ev('(bbc-load "'+(PROGRAMS/'mandelbrot-terminal.bas').as_posix()+'")')

    def render(self, language, colour):
        if language == 'lisp':
            return self.capture(f'(mandelbrot-terminal {"#t" if colour else "#f"} 31 13 40)')
        return self.capture('(bbc-run "PROCmandelbrot('+('TRUE' if colour else 'FALSE')+',31,13,40)")')

    def test_plain_versions_match_mathematical_reference(self):
        self.load_renderers()
        ramp = '.,:;ox%#@'
        rows = []
        for row in range(13):
            line = ''
            for col in range(31):
                c = complex(-2.2+3.0*col/30, -1.0+2.0*row/12)
                z, count = 0j, 0
                while count < 40 and abs(z)**2 <= 4:
                    z = z*z+c
                    count += 1
                line += ' ' if count == 40 else ramp[count % len(ramp)]
            rows.append(line)
        expected = '\n'.join(rows)+'\n'
        for language in ('lisp', 'basic'):
            with self.subTest(language=language):
                output = self.render(language, False)
                self.assertEqual(output, expected)
                self.assertNotIn('\x1b', output)

    def test_coloured_versions_keep_shape_and_restore_attributes(self):
        self.load_renderers()
        plain = self.render('lisp', False)
        outputs = []
        for language in ('lisp', 'basic'):
            with self.subTest(language=language):
                output = self.render(language, True)
                self.assertEqual(ANSI.sub('', output), plain)
                self.assertIn('\x1b[40m', output)
                self.assertRegex(output, r'\x1b\[9[1-6]m')
                self.assertTrue(output.endswith('\x1b[0m'))
                outputs.append(output)
        self.assertEqual(*outputs)

    def test_escape_counts_for_known_points_including_boundary(self):
        self.load_renderers()
        for cx, cy, expected in ((0, 0, 40), (-1, 0, 40), (-2, 0, 40), (2, 2, 1), (2, 0, 2)):
            with self.subTest(cx=cx, cy=cy):
                self.assertEqual(self.ev(f'(mandelbrot-terminal-escape {cx} {cy} 40)'), expected)
                self.assertEqual(self.capture(f'(bbc-run "PRINT ;FNmandelEscape({cx},{cy},40)")'), str(expected)+'\n')

    def test_four_launchers_render_default_dimensions(self):
        for filename in ('mandelbrot-terminal.lisp', 'mandelbrot-terminal-colour.lisp',
                         'mandelbrot-basic-terminal.lisp', 'mandelbrot-basic-terminal-colour.lisp'):
            with self.subTest(filename=filename), contextlib.redirect_stdout(io.StringIO()) as out:
                lispy3.load_workspace(str(PROGRAMS/filename))
                rows = ANSI.sub('', out.getvalue()).splitlines()
                self.assertEqual(len(rows), 25)
                self.assertTrue(all(len(row) == 79 for row in rows))
