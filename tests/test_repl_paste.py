"""Terminal paste handling and GNU readline bracketed-paste configuration."""
import contextlib
import io
import types
from unittest.mock import patch
from support import LispyTestCase, lispy3


class ReplPasteTest(LispyTestCase):
    def run_repl(self, *chunks):
        prompts = []
        def read(prompt):
            prompts.append(prompt)
            return next(inputs)
        inputs = iter([*chunks, 'exit'])
        output = io.StringIO()
        with patch('builtins.input', side_effect=read), patch.object(lispy3, 'setup_completion', return_value=False), contextlib.redirect_stdout(output):
            lispy3.repl()
        return output.getvalue(), prompts

    def test_pasted_block_evaluates_every_top_level_form(self):
        output, _ = self.run_repl('(define paste-value 10)\n(+ paste-value 1)\n(+ paste-value 2)')
        self.assertIn('11', output)
        self.assertIn('12', output)

    def test_pasted_definitions_exist_before_later_macro_expansion(self):
        output, _ = self.run_repl('(define (paste-helper) 42)\n(define-macro (paste-m) (paste-helper))\n(paste-m)')
        self.assertIn('42', output)
        self.assertNotIn('Error:', output)

    def test_comments_and_multiline_definition_need_no_extra_prompt(self):
        output, prompts = self.run_repl('; a pasted block\n(define (paste-f x)\n  (+ x 1))\n(paste-f 9)\n; end')
        self.assertIn('10', output)
        self.assertNotIn('Error:', output)
        self.assertEqual(len(prompts), 2)

    def test_typed_continuation_still_works(self):
        output, prompts = self.run_repl('(define (paste-f x)', '(+ x 1))', '(paste-f 5)')
        self.assertIn('6', output)
        self.assertIn('... (1)>', prompts[1])

    def test_malformed_tail_is_reported_before_any_form_executes(self):
        output, _ = self.run_repl('(define should-not-exist 1) )')
        self.assertIn('Error:', output)
        self.assertNotIn('should-not-exist', lispy3.global_env)


class ReadlinePasteTest(LispyTestCase):
    def configure(self, doc, platform):
        commands = []
        module = types.SimpleNamespace(__doc__=doc, parse_and_bind=commands.append,
            set_completer=lambda value: None, set_completer_delims=lambda value: None)
        with patch.dict('sys.modules', {'readline': module}), patch.object(lispy3.sys, 'platform', platform):
            self.assertTrue(lispy3.setup_completion())
        return commands

    def test_gnu_readline_enables_bracketed_paste(self):
        self.assertIn('set enable-bracketed-paste on', self.configure('GNU readline', 'linux'))

    def test_libedit_and_windows_do_not_receive_gnu_only_setting(self):
        self.assertNotIn('set enable-bracketed-paste on', self.configure('libedit', 'darwin'))
        self.assertNotIn('set enable-bracketed-paste on', self.configure('pyreadline3', 'win32'))
