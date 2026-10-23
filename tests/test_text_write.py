"""Common Lisp text WRITE must not call turtle.WRITE."""
import contextlib
import io
from unittest.mock import patch
from support import LispyTestCase, lispy3 as L


class TextWriteTest(LispyTestCase):
    def test_text_write_returns_object_without_newline_or_turtle(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            value = self.ev('(write (list 5 7 8))')
        self.assertEqual(out.getvalue(), '(5 7 8)')
        self.assertEqual(value, [5, 7, 8])
        self.assertEqual(L.turtle.calls, [])

    def test_strings_are_printed_readably(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            value = self.ev('(write "Hello")')
        self.assertEqual(out.getvalue(), '"Hello"')
        self.assertEqual(value, L.String('Hello'))

    def test_turtle_write_has_explicit_name_even_when_text_write_exists(self):
        with patch.object(L.turtle, 'write', create=True) as drawing, patch.object(L.turtle, '__all__', list(L.turtle.__all__)+['write']):
            env = L.standard_env()
            L.eval_exp(L.parse('(turtle:write "Hello")'), env)
            drawing.assert_called_once_with('Hello')
            self.assertIs(env['write'].native_fn, L._write_text)

    def test_gui_marshals_drawing_write_but_keeps_text_in_worker_output(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from test_machine_args import machine
        text = L.Procedure(['*args'], None, L.global_env, native_fn=L._write_text, name='write')
        drawing_fn = Mock()
        drawing_fn.on_main = False
        drawing = L.Procedure(['*args'], None, L.global_env, native_fn=drawing_fn, name='turtle:write')
        wrapped = Mock()
        app = SimpleNamespace(_on_main_fn=Mock(return_value=wrapped))
        machine.LispMachine._gui_builtins_on_main(app, {'write': text, 'dot': text, 'turtle:write': drawing})
        self.assertIs(text.native_fn, L._write_text)
        self.assertIs(drawing.native_fn, wrapped)
        app._on_main_fn.assert_called_once_with(drawing_fn)

    def test_turtle_dot_is_explicit_and_not_a_bare_graphics_alias(self):
        self.ev('(turtle:dot 2 "black")')
        self.assertIn(('dot', (2, 'black')), L.turtle.calls)
        drawing = L.global_env['turtle:dot']
        self.assertIsNot(L.global_env.get('dot'), drawing)
