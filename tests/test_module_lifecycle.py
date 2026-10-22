import tempfile
from pathlib import Path
from support import LispyTestCase, lispy3 as r


class ModuleLifecycleTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        r.library_system.reset()
        self.saved_macros = r.macro_table.copy()
        self.addCleanup(lambda: (r.macro_table.clear(), r.macro_table.update(self.saved_macros)))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'module.lisp'
        self.spec = r.String(self.path.as_posix())

    def source(self, text):
        self.path.write_text(text, encoding='utf-8')

    def imp(self, selection=None):
        r.library_system.import_sets([selection or self.spec])

    def test_private_cached_state_and_macro(self):
        self.source('(define n 0) (define (next) (set! n (+ n 1)) n) (define-macro (answer) 42)')
        self.imp(['prefix', self.spec, 'm:'])
        self.assertEqual(self.ev('(m:next)'), 1)
        self.imp(['prefix', self.spec, 'm:'])
        self.assertEqual(self.ev('(m:next)'), 2)
        self.assertEqual(self.ev('(m:answer)'), 42)
        self.assertNotIn('n', r.global_env)
        self.assertNotIn('m:+', r.global_env)

    def test_reload_selection_and_fresh_state(self):
        self.source('(define old 1) (define kept 2)')
        self.imp(['prefix', ['rename', self.spec, ['kept', 'alias']], 'm:'])
        self.source('(define kept 20) (define added 30)')
        r.library_system.reload(self.spec)
        self.assertEqual(self.ev('m:alias'), 20)
        self.assertEqual(self.ev('m:added'), 30)
        self.assertNotIn('m:old', r.global_env)

    def test_unload_identity_and_macro_identity(self):
        self.source('(define x 1) (define-macro (m) 2)')
        self.imp()
        r.global_env['x'] = 99
        replacement = object()
        r.macro_table['m'] = replacement
        r.library_system.unload(self.spec)
        self.assertEqual(r.global_env['x'], 99)
        self.assertIs(r.macro_table['m'], replacement)
        self.assertFalse(r.library_system.files)

    def test_failed_reload_retains_registry_and_imports(self):
        self.source('(define x 1)')
        self.imp()
        old = dict(r.library_system.registry)
        self.source('(define x missing)')
        with self.assertRaises(NameError):
            r.library_system.reload(self.spec)
        self.assertEqual(r.library_system.registry, old)
        self.assertEqual(self.ev('x'), 1)

    def test_dependencies_not_exported_and_unload_refused(self):
        dep = Path(self.tmp.name) / 'dep.lisp'
        dep.write_text('(define x 3)', encoding='utf-8')
        self.source('(import "dep.lisp") (define y (+ x 1))')
        self.imp()
        self.assertEqual(self.ev('y'), 4)
        self.assertNotIn('x', r.global_env)
        with self.assertRaisesRegex(Exception, 'depend|imported by'):
            r.library_system.unload(r.String(dep.as_posix()))
        r.library_system.unload(self.spec)
        r.library_system.unload(r.String(dep.as_posix()))

    def test_builtin_redefinition_is_exported_and_isolated(self):
        self.source('(define (+ x) x) (define eval 17)')
        self.imp(['prefix', self.spec, 'm:'])
        self.assertEqual(self.ev('(m:+ 7)'), 7)
        self.assertEqual(self.ev('m:eval'), 17)
        self.assertEqual(self.ev('(+ 1 2)'), 3)

    def test_named_library_unload(self):
        self.ev('(define-library sample (export x) (begin (define x 3)))')
        self.ev('(import sample)')
        r.library_system.unload('sample')
        self.assertNotIn('x', r.global_env)
    def test_cleanup_order_scope_once_and_recursive_guard(self):
        self.source('(define x 1)')
        self.imp()
        system = r.library_system
        old = system._loaded(self.spec)
        calls = []
        def callback():
            calls.append(system.evaluate('x', old))
            with self.assertRaisesRegex(Exception, 'cleanup'):
                system.unload(self.spec)
            with self.assertRaisesRegex(Exception, 'cleanup'):
                system.reload(self.spec)
        with system.scope(old):
            system.on_unload(lambda: calls.append('first'))
            system.on_unload(callback)
        self.source('(define x 2)')
        system.reload(self.spec)
        self.assertEqual(calls, [1, 'first'])
        self.assertEqual(self.ev('x'), 2)
        system.unload(self.spec)
        self.assertEqual(calls, [1, 'first'])

    def test_cleanup_errors_commit_and_remaining_callbacks_run(self):
        self.source('(define x 1)')
        self.imp()
        system = r.library_system
        calls = []
        def broken():
            raise ValueError('cleanup boom')
        with system.scope(system._loaded(self.spec)):
            system.on_unload(lambda: calls.append('done'))
            system.on_unload(broken)
        with self.assertRaisesRegex(Exception, 'cleanup.*boom'):
            system.unload(self.spec)
        self.assertEqual(calls, ['done'])
        self.assertNotIn('x', r.global_env)
        self.assertFalse(system.registry)

    def test_cleanup_all_and_registration_validation(self):
        system = r.library_system
        with self.assertRaisesRegex(Exception, 'scope'):
            system.on_unload(lambda: None)
        self.source('(define x 1)')
        self.imp()
        calls = []
        with system.scope(system._loaded(self.spec)):
            with self.assertRaisesRegex(Exception, 'callable|procedure'):
                system.on_unload(1)
            system.on_unload(lambda: calls.append('done'))
        system.cleanup_all()
        system.cleanup_all()
        self.assertEqual(calls, ['done'])
        self.assertNotIn('x', r.global_env)
        self.assertFalse(system.registry)
    def test_only_does_not_gain_exports_and_removed_alias_disappears(self):
        self.source('(define x 1) (define y 2)')
        self.imp(['rename', ['only', self.spec, 'x'], ['x', 'alias']])
        self.source('(define y 20) (define z 30)')
        r.library_system.reload(self.spec)
        self.assertNotIn('alias', r.global_env)
        self.assertNotIn('z', r.global_env)

    def test_reload_collision_is_atomic(self):
        self.source('(define x 1)')
        self.imp()
        self.ev('(define y 99)')
        old = r.library_system._loaded(self.spec)
        self.source('(define x 2) (define y 3)')
        with self.assertRaisesRegex(Exception, 'collision'):
            r.library_system.reload(self.spec)
        self.assertIs(r.library_system._loaded(self.spec), old)
        self.assertEqual(self.ev('x'), 1)
        self.assertEqual(self.ev('y'), 99)

    def test_macro_reload_and_no_stale_private_state(self):
        self.source('(define secret 7) (define-macro (m) secret)')
        self.imp(['prefix', self.spec, 'p:'])
        self.assertEqual(self.ev('(p:m)'), 7)
        self.source('(define-macro (m) 9)')
        r.library_system.reload(self.spec)
        self.assertEqual(self.ev('(p:m)'), 9)
        self.assertNotIn('secret', r.library_system._loaded(self.spec).env)
        r.library_system.unload(self.spec)
        self.assertNotIn('p:m', r.macro_table)

    def test_workspace_object_swap_uses_current_environment(self):
        self.source('(define x 1)')
        self.imp()
        previous = r.global_env
        r.global_env = r.Env(outer=r.standard_env())
        r.global_env.update(previous)
        try:
            r.library_system.unload(self.spec)
            self.assertNotIn('x', r.global_env)
            self.assertIn('x', previous)
        finally:
            r.global_env = previous

    def test_reload_cleanup_error_retains_new_instance_and_old_eval_load_scope(self):
        self.source('(define x 1)')
        self.imp()
        system = r.library_system
        old = system._loaded(self.spec)
        included = Path(self.tmp.name) / 'cleanup.lisp'
        included.write_text('(define cleaned x)', encoding='utf-8')
        def callback():
            system.evaluate(r.read_from_tokens(r.tokenize('(load "cleanup.lisp" :silent)')), old)
            self.assertEqual(old.env['cleaned'], 1)
            raise ValueError('old cleanup failed')
        with system.scope(old):
            system.on_unload(callback)
        self.source('(define x 2)')
        with self.assertRaisesRegex(Exception, 'committed.*old cleanup failed'):
            system.reload(self.spec)
        self.assertEqual(self.ev('x'), 2)
        self.assertNotIn('cleaned', system._loaded(self.spec).env)
        self.assertFalse(old.cleanup)

    def test_file_side_effects_cached_and_reload_reexecutes(self):
        import contextlib
        import io
        self.source('(display "module ran") (define x 1)')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.imp()
            self.imp()
            r.library_system.reload(self.spec)
        self.assertEqual(output.getvalue(), 'module ran\nmodule ran\n')

    def test_sld_reload_by_symbol_preserves_selection(self):
        path = Path(self.tmp.name) / 'named.sld'
        path.write_text('(define-library named (export x) (begin (define x 1)))', encoding='utf-8')
        r.library_system.import_sets([['prefix', r.String(path.as_posix()), 'n:']])
        path.write_text('(define-library named (export y) (begin (define y 2)))', encoding='utf-8')
        r.library_system.reload('named')
        self.assertNotIn('n:x', r.global_env)
        self.assertEqual(self.ev('n:y'), 2)
        r.library_system.unload('named')
        self.assertNotIn('n:y', r.global_env)
    def test_failed_reload_keeps_old_cleanup_and_cleans_staged_resources(self):
        from unittest.mock import patch
        system = r.library_system
        calls = []
        standard = r.standard_env
        def environment():
            env = standard()
            env['register-cleanup'] = lambda: system.on_unload(lambda: calls.append('staged'))
            return env
        self.source('(define x 1)')
        self.imp()
        old = system._loaded(self.spec)
        with system.scope(old):
            system.on_unload(lambda: calls.append('old'))
        self.source('(register-cleanup) (define x missing)')
        with patch.object(r, 'standard_env', environment):
            with self.assertRaises(NameError):
                system.reload(self.spec)
        self.assertEqual(calls, ['staged'])
        self.assertIs(system._loaded(self.spec), old)
        system.unload(self.spec)
        self.assertEqual(calls, ['staged', 'old'])

    def test_cleanup_all_dependents_before_dependencies_and_continues_on_error(self):
        system = r.library_system
        self.ev('(define-library dep (export x) (begin (define x 1)))')
        self.ev('(define-library client (import dep) (export y) (begin (define y x)))')
        calls = []
        def broken():
            calls.append('client')
            raise ValueError('failed')
        with system.scope(system.registry['dep']):
            system.on_unload(lambda: calls.append('dep'))
        with system.scope(system.registry['client']):
            system.on_unload(broken)
        with self.assertRaisesRegex(Exception, 'cleanup.*failed'):
            system.cleanup_all()
        self.assertEqual(calls, ['client', 'dep'])
        self.assertFalse(system.registry)
        system.cleanup_all()

    def test_reload_refuses_live_library_dependents(self):
        self.source('(define x 1)')
        self.imp()
        self.ev('(define-library client (import "' + self.path.as_posix() + '") (export x))')
        with self.assertRaisesRegex(Exception, 'dependent.*client'):
            r.library_system.reload(self.spec)
        self.assertEqual(self.ev('x'), 1)

    def test_file_errors_include_path_and_sld_requires_wrapper(self):
        path = Path(self.tmp.name) / 'bad.sld'
        path.write_text('(define x 1)', encoding='utf-8')
        with self.assertRaisesRegex(Exception, 'bad[.]sld.*define-library'):
            r.library_system.import_sets([r.String(path.as_posix())])

    def test_standard_environments_are_distinct(self):
        self.source('(define x 1)')
        self.imp()
        first = r.library_system._loaded(self.spec)
        second_path = Path(self.tmp.name) / 'other.lisp'
        second_path.write_text('(define y 2)', encoding='utf-8')
        r.library_system.import_sets([r.String(second_path.as_posix())])
        second = r.library_system._loaded(r.String(second_path.as_posix()))
        self.assertIsNot(first.env.outer, second.env.outer)
        self.assertIsNot(first.env.outer, r.global_env)
    def test_reload_preserves_overwritten_value_and_macro(self):
        self.source('(define x 1) (define-macro (m) 2)')
        self.imp()
        replacement = object()
        r.global_env['x'] = 99
        r.macro_table['m'] = replacement
        self.source('(define x 3) (define-macro (m) 4)')
        r.library_system.reload(self.spec)
        self.assertEqual(r.global_env['x'], 99)
        self.assertIs(r.macro_table['m'], replacement)

    def test_failed_named_export_validation_runs_cleanup(self):
        from unittest.mock import patch
        system = r.library_system
        calls = []
        standard = r.standard_env
        def environment():
            env = standard()
            env['register-cleanup'] = lambda: system.on_unload(lambda: calls.append('done'))
            return env
        with patch.object(r, 'standard_env', environment):
            with self.assertRaisesRegex(Exception, 'missing'):
                self.ev('(define-library bad (export missing) (begin (register-cleanup)))')
        self.assertEqual(calls, ['done'])
        self.assertNotIn('bad', system.registry)

    def test_cleanup_all_callbacks_can_call_imported_dependency(self):
        system = r.library_system
        for fail in (False, True):
            with self.subTest(callback_fails=fail):
                self.ev('''(define-library resource-b (export release)
                  (begin (define released 0)
                    (define (release) (set! released (+ released 1)))))''')
                body = '(release) missing-cleanup-value' if fail else '(release)'
                self.ev('''(define-library resource-a (import resource-b)
                  (export cleanup)
                  (begin (define (cleanup) ''' + body + ')))')
                self.ev('(import (prefix resource-a a:))')
                dependency = system.registry['resource-b']
                client = system.registry['resource-a']
                observed = []
                with system.scope(dependency):
                    system.on_unload(lambda: observed.append(dependency.env['released']))
                with system.scope(client):
                    system.on_unload(client.env['cleanup'])
                if fail:
                    with self.assertRaisesRegex(Exception, 'missing-cleanup-value'):
                        system.cleanup_all()
                else:
                    system.cleanup_all()
                self.assertEqual(observed, [1])
                self.assertNotIn('release', client.env)
                self.assertNotIn('a:cleanup', r.global_env)
                self.assertFalse(system.registry)
                self.assertFalse(system.files)
                self.assertFalse(system.imports)
                system.cleanup_all()
                self.assertEqual(observed, [1])

    def test_cleanup_rejects_module_creation_and_runs_remaining_callbacks(self):
        system = r.library_system
        self.source('(define x 1)')
        self.imp()
        fresh = Path(self.tmp.name) / 'fresh.lisp'
        fresh.write_text('(define fresh-value 2)', encoding='utf-8')
        fresh_spec = r.String(fresh.as_posix())
        library = system._loaded(self.spec)
        attempts = []
        calls = []
        def forbidden(action):
            try:
                action()
            except Exception as exc:
                attempts.append(str(exc))
                raise
        with system.scope(library):
            system.on_unload(lambda: calls.append('remaining'))
            system.on_unload(lambda: forbidden(lambda: system.resolve(fresh_spec)))
            system.on_unload(lambda: forbidden(lambda: system.define(
                ['define-library', 'fresh-named', ['export']])))
            system.on_unload(lambda: forbidden(lambda: system.import_sets([fresh_spec])))
        with self.assertRaisesRegex(Exception, 'cleanup.*lifecycle|lifecycle.*cleanup'):
            system.cleanup_all()
        self.assertEqual(len(attempts), 3)
        self.assertTrue(all('cleanup' in error and 'lifecycle' in error for error in attempts))
        self.assertEqual(calls, ['remaining'])
        self.assertFalse(system.registry)
        self.assertFalse(system.files)
        self.assertFalse(system.imports)
        self.assertNotIn('fresh-value', r.global_env)

    def test_named_cleanup_order_follows_dependencies_not_registry_order(self):
        system = r.library_system
        self.ev('''(define-library ordered-b (export require-open close)
          (begin (define open #t)
            (define (require-open) (if open #t dependency-already-closed))
            (define (close) (set! open #f))))''')
        self.ev('''(define-library ordered-a (import ordered-b) (export cleanup)
          (begin (define cleaned #f)
            (define (cleanup) (require-open) (set! cleaned #t))))''')
        dependency = system.registry['ordered-b']
        client = system.registry['ordered-a']
        # Deliberately use A,B insertion order: lifecycle ordering must use
        # import records, regardless of when a loader publishes named libraries.
        system.registry.clear()
        system.registry.update({'ordered-a': client, 'ordered-b': dependency})
        with system.scope(dependency):
            system.on_unload(dependency.env['close'])
        with system.scope(client):
            system.on_unload(client.env['cleanup'])
        system.cleanup_all()
        self.assertTrue(client.env['cleaned'])
        self.assertFalse(dependency.env['open'])
        self.assertFalse(system.registry)
        self.assertFalse(system.imports)
