"""Workspace contract; install explicitly without changing runtime defaults."""
import unittest
from support import lispy3 as runtime
from lispy_support.lispy_workspaces import WorkspaceManager


def install_manager(runtime):
    """Parent glue: construct only after runtime.library_system exists."""
    return WorkspaceManager(runtime)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        saved = (runtime.global_env, runtime.macro_table, runtime.library_system)
        self.addCleanup(self.restore, saved)
        runtime.global_env = runtime.standard_env()
        runtime.macro_table = {}
        runtime.library_system = runtime.LibrarySystem(runtime)
        self.manager = install_manager(runtime)

    def restore(self, saved):
        runtime.global_env, runtime.macro_table, runtime.library_system = saved

    def ev(self, source):
        return runtime.eval_exp(runtime.parse(source), runtime.global_env)

    def test_exact_restoration_with_closures_and_mutable_values(self):
        old = self.manager.capture()
        self.ev('(define n 3)')
        self.ev('(define (next) (set! n (+ n 1)) n)')
        closure = old.env['next']
        data = old.env['data'] = [1]
        self.manager.push()
        runtime.global_env['n'] = 999
        self.assertIs(self.manager.pop(), old)
        self.assertIs(runtime.global_env, old.env)
        self.assertIs(runtime.macro_table, old.macro_table)
        self.assertIs(runtime.library_system, old.library_system)
        self.assertIs(old.env['next'], closure)
        self.assertIs(old.env['data'], data)
        self.assertIs(closure.env, old.env)
        self.assertEqual(self.ev('(next)'), 4)

    def test_fresh_workspace_has_no_basic_or_library_bindings(self):
        self.ev('(import (only mini-basic bbc-run))')
        self.ev('(define basic-user-state 12)')
        self.assertIn('bbc-run', runtime.macro_table)
        old = self.manager.current
        fresh = self.manager.push()
        self.assertIsNot(fresh.env, old.env)
        self.assertIsNone(fresh.env.outer)
        for name in ('bbc-run', 'basic-user-state', 'bbc-print-value'):
            self.assertNotIn(name, fresh.env)
        self.assertEqual(fresh.macro_table, {})
        self.assertEqual(fresh.library_system.registry, {})
        self.assertEqual(self.ev('(+ 2 3)'), 5)
        self.manager.pop()
        self.assertIn('bbc-run', runtime.macro_table)

    def test_macros_and_library_registries_are_independent(self):
        self.ev('(define-macro (answer) 42)')
        self.ev('(define-library sample (export x) (begin (define x 7)))')
        old = self.manager.current
        new = self.manager.push()
        self.assertIsNot(new.macro_table, old.macro_table)
        self.assertIsNot(new.library_system, old.library_system)
        self.assertNotIn('answer', new.macro_table)
        self.assertNotIn('sample', new.library_system.registry)
        self.ev('(define-macro (answer) 99)')
        self.ev('(define-library sample (export x) (begin (define x 8)))')
        self.manager.pop()
        self.assertEqual(self.ev('(answer)'), 42)
        self.ev('(import sample)')
        self.assertEqual(self.ev('x'), 7)

    def test_failed_pop_changes_nothing(self):
        old = self.manager.capture()
        with self.assertRaises(IndexError):
            self.manager.pop()
        self.assertIs(self.manager.current, old)
        self.assertIs(runtime.global_env, old.env)
        self.assertIs(runtime.macro_table, old.macro_table)
        self.assertIs(runtime.library_system, old.library_system)

    def test_cleanup_once_on_discard_never_on_push(self):
        calls = []
        old = self.manager.current
        old.add_cleanup(lambda: calls.append('old'))
        temporary = self.manager.push()
        temporary.add_cleanup(lambda: calls.append('temporary'))
        self.assertEqual(calls, [])
        self.manager.pop()
        self.assertEqual(calls, ['temporary'])
        self.manager.discard(temporary)
        self.assertEqual(calls, ['temporary'])
        with self.assertRaises(ValueError):
            self.manager.discard(old)

    def test_use_restores_after_exception_without_discard(self):
        old = self.manager.current
        with self.manager.use(old):
            other = self.manager.push()
        calls = []
        other.add_cleanup(lambda: calls.append(1))
        with self.assertRaisesRegex(RuntimeError, 'body'):
            with self.manager.use(other) as selected:
                self.assertIs(selected, other)
                self.assertIs(runtime.global_env, other.env)
                with self.manager.use(old):
                    self.assertIs(self.manager.current, old)
                raise RuntimeError('body')
        self.assertIs(self.manager.current, old)
        self.assertEqual(calls, [])
        self.manager.discard(other)
        self.assertEqual(calls, [1])

    def test_initializers_run_only_on_fresh_creation_in_workspace(self):
        calls = []
        old = self.manager.current
        def initialize(workspace):
            self.assertIs(runtime.global_env, workspace.env)
            self.assertIs(self.manager.current, workspace)
            workspace.env['extension'] = []
            calls.append(workspace)
        self.manager.workspace_initializers.append(initialize)
        with self.manager.use(old):
            a = self.manager.push()
            b = self.manager.push()
        self.assertIs(self.manager.current, old)
        self.assertIsNot(a.env['extension'], b.env['extension'])
        with self.manager.use(a):
            pass
        self.assertEqual(calls, [a, b])

    def test_initializer_failure_restores_and_cleans_resources(self):
        old = self.manager.current
        calls = []
        def fail(workspace):
            workspace.add_cleanup(lambda: calls.append('closed'))
            raise RuntimeError('initializer')
        self.manager.workspace_initializers.append(fail)
        with self.assertRaisesRegex(RuntimeError, 'initializer'):
            self.manager.push()
        self.assertIs(self.manager.current, old)
        self.assertIs(runtime.global_env, old.env)
        self.assertEqual(calls, ['closed'])
        with self.assertRaises(IndexError):
            self.manager.pop()

    def test_cleanup_failure_still_restores_and_runs_remaining_callbacks(self):
        old = self.manager.current
        calls = []
        temporary = self.manager.push()
        temporary.add_cleanup(lambda: calls.append('closed'))
        def fail():
            raise RuntimeError('cleanup')
        temporary.add_cleanup(fail)
        with self.assertRaisesRegex(RuntimeError, 'cleanup'):
            self.manager.pop()
        self.assertIs(self.manager.current, old)
        self.assertIs(runtime.global_env, old.env)
        self.assertEqual(calls, ['closed'])
        self.manager.discard(temporary)


    def test_public_initializers_and_discard_callbacks(self):
        calls = []
        self.manager.add_initializer(lambda env: env.update(extension=[]))
        old = self.manager.current
        self.manager.on_discard(lambda: calls.append(self.manager.current))
        fresh = self.manager.new_workspace('fresh')
        self.assertEqual(calls, [old])
        self.assertIs(self.manager.current, fresh)
        self.assertEqual(fresh.name, 'fresh')
        self.assertIn('extension', fresh.env)
        self.assertIs(runtime.global_env, fresh.env)
        self.assertIs(runtime.macro_table, fresh.macro_table)
        self.assertIs(runtime.library_system, fresh.library_system)
        self.manager.discard(old)
        self.assertEqual(calls, [old])

    def test_lisp_cleanup_runs_in_departing_workspace(self):
        old = self.manager.current
        temporary = self.manager.push('temporary')
        data = temporary.env['events'] = []
        self.ev('(define-macro (answer) 17)')
        self.ev('(define-library cleanup-lib (export x) (begin (define x 1)))')
        self.ev('(import cleanup-lib)')
        # Use a native collector while the Lisp Procedure resolves its own macro.
        temporary.env['record'] = runtime.Procedure(
            parms=['x'], body=None, env=temporary.env,
            native_fn=lambda x: data.append(x), name='record')
        callback = self.ev('(lambda () (record (answer)))')
        self.manager.on_discard(callback)
        self.manager.pop()
        self.assertEqual(data, [17])
        self.assertIs(self.manager.current, old)
        self.assertIn('cleanup-lib', temporary.library_system.registry)

    def test_push_and_use_never_run_public_discard_callback(self):
        calls = []
        old = self.manager.current
        self.manager.on_discard(lambda: calls.append('old'))
        temporary = self.manager.push()
        with self.manager.use(old):
            pass
        self.assertEqual(calls, [])
        self.manager.pop()
        self.assertIs(self.manager.current, old)
        self.assertEqual(calls, [])

    def test_new_preserves_saved_stack_and_exposes_depth(self):
        old = self.manager.current
        old.env['data'] = data = [1]
        registry = old.library_system.registry
        self.assertEqual(self.manager.depth, 0)
        temporary = self.manager.push('temporary')
        self.assertEqual(self.manager.depth, 1)
        calls = []
        self.manager.on_discard(lambda: calls.append(self.manager.current))
        fresh = self.manager.new('replacement')
        self.assertEqual(calls, [temporary])
        self.assertEqual(fresh.name, 'replacement')
        self.assertEqual(self.manager.depth, 1)
        self.assertIs(self.manager.pop(), old)
        self.assertEqual(self.manager.depth, 0)
        self.assertIs(old.env['data'], data)
        self.assertEqual(data, [1])
        self.assertIs(old.library_system.registry, registry)

    def test_cleanup_rejects_all_transitions_and_continues_after_failure(self):
        old = self.manager.current
        departing = self.manager.push()
        calls = []
        def check_transitions():
            for action in (self.manager.new, self.manager.new_workspace,
                           self.manager.push, self.manager.pop,
                           lambda: self.manager.discard(old)):
                with self.assertRaisesRegex(RuntimeError, 'cleanup'):
                    action()
            with self.assertRaisesRegex(RuntimeError, 'cleanup'):
                with self.manager.use(old):
                    pass
            self.assertIs(self.manager.current, departing)
            self.assertIs(runtime.library_system, departing.library_system)
            calls.append('checked')
        self.manager.on_discard(check_transitions)
        def fail():
            raise RuntimeError('resource failure')
        self.manager.on_discard(fail)
        with self.assertRaisesRegex(RuntimeError, 'resource failure'):
            self.manager.pop()
        self.assertEqual(calls, ['checked'])
        self.assertIs(self.manager.current, old)
        self.assertEqual(self.manager.depth, 0)
        self.manager.discard(departing)
        self.assertEqual(calls, ['checked'])

    def test_new_cleanup_failure_still_activates_fresh_state(self):
        old = self.manager.current
        self.manager.push()
        departing = self.manager.current
        def fail():
            self.assertIs(runtime.global_env, departing.env)
            raise RuntimeError('release')
        self.manager.on_discard(fail)
        with self.assertRaisesRegex(RuntimeError, 'release'):
            self.manager.new('fresh')
        self.assertEqual(self.manager.current.name, 'fresh')
        self.assertIs(runtime.global_env, self.manager.current.env)
        self.assertIsNot(self.manager.current, departing)
        self.assertEqual(self.manager.depth, 1)
        self.assertIs(self.manager.pop(), old)

    def test_borrowed_saved_workspace_cannot_be_reset_or_discarded(self):
        old = self.manager.current
        current = self.manager.push()
        with self.manager.use(old):
            with self.assertRaises(ValueError):
                self.manager.new()
            self.assertIs(self.manager.current, old)
        self.assertIs(self.manager.current, current)
        self.assertEqual(self.manager.depth, 1)
        self.assertIs(self.manager.pop(), old)
