from unittest import TestCase
from unittest.mock import patch
import io
from support import lispy3 as L

class WorkspaceCommandTest(TestCase):
    def setUp(self):
        self.saved = (L.global_env, L.macro_table, L.library_system, getattr(L, 'workspaces', None))
        if hasattr(L, 'workspaces'):
            from lispy_workspaces import WorkspaceManager
            L.workspaces = WorkspaceManager(L)
            L.workspaces.add_initializer(L._workspace_library_cleanup)
            L._workspace_library_cleanup(L.global_env)
            L.workspaces.new()
    def tearDown(self):
        L.global_env, L.macro_table, L.library_system, manager = self.saved
        if manager is not None: L.workspaces = manager
    def ev(self, source):
        return L.eval_exp(L.parse(source))
    def test_new_has_no_old_loop_counter_or_user_macro(self):
        self.ev('(define i 73)')
        self.ev('(define-macro (answer) 42)')
        self.ev('(new-workspace)')
        with self.assertRaises(NameError): self.ev('i')
        self.assertNotIn('answer', L.macro_table)
        self.assertEqual(self.ev('(+ 2 3)'), 5)
    def test_push_pop_restores_closure_mutation_and_memo_cache(self):
        self.ev('(define count 1)')
        self.ev('(define-memo (counted n) (set! count (+ count 1)) (* n n))')
        self.assertEqual(self.ev('(counted 9)'), 81)
        old = L.global_env; memo = old['counted']
        self.ev('(workspace-push)')
        self.ev('(define count 999)')
        self.ev('(workspace-pop)')
        self.assertIs(L.global_env, old)
        self.assertIs(L.global_env['counted'], memo)
        self.assertEqual(self.ev('(counted 9)'), 81)
        self.assertEqual(self.ev('count'), 2)
    def test_cleanup_once_on_pop_and_never_on_push(self):
        events = []
        L.global_env['record'] = lambda: events.append('closed')
        self.ev('(workspace-on-discard record)')
        self.ev('(workspace-push)')
        self.assertEqual(events, [])
        self.ev('(workspace-pop)')
        self.assertEqual(events, [])
        self.ev('(new-workspace)')
        self.assertEqual(events, ['closed'])
    def test_transitions_are_standalone_commands(self):
        with self.assertRaisesRegex(SyntaxError, 'standalone'):
            self.ev('(begin (workspace-push) (define lost 1))')
        with self.assertRaisesRegex(SyntaxError, 'top.level'):
            self.ev('(define (bad) (new-workspace))')
    def test_repl_refreshes_active_environment_after_push_pop(self):
        lines = ['(define old 7)', '(workspace-push)', '(define old 99)', '(workspace-pop)', 'old', 'exit']
        with patch('builtins.input', side_effect=lines), patch.object(L, 'setup_completion', return_value=False), patch('sys.stdout', new_callable=io.StringIO) as output:
            L.repl()
        self.assertEqual(self.ev('old'), 7)
        self.assertNotIn('Undefined symbol', output.getvalue())

    def test_dynamic_eval_cannot_replace_environment_inside_running_form(self):
        old = L.global_env
        with self.assertRaisesRegex(L.LispyError, 'standalone'):
            self.ev("(eval '(workspace-push))")
        self.assertIs(L.global_env, old)

    def test_discard_runs_imported_module_cleanup(self):
        import tempfile
        from pathlib import Path
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory)/'resource.lisp'
            module.write_text('(module-on-unload (lambda () (display "released"))) (define value 1)')
            self.ev('(import (prefix "'+module.as_posix()+'" resource:))')
            with redirect_stdout(io.StringIO()) as output:
                self.ev('(new-workspace)')
            self.assertEqual(output.getvalue(), 'released\n')
            self.assertNotIn('resource:value', L.global_env)

    def test_unload_reload_forms_refresh_private_file_module(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory)/'data.lisp'
            module.write_text('(define value 1)')
            quoted = '"'+module.as_posix()+'"'
            self.ev('(import (prefix '+quoted+' m:))')
            module.write_text('(define value 2)')
            self.ev('(reload '+quoted+')')
            self.assertEqual(self.ev('m:value'), 2)
            self.ev('(unload '+quoted+')')
            with self.assertRaises(NameError): self.ev('m:value')
