"""Explicit libraries isolate helpers and import public values/macros selectively."""
import contextlib
import io
import tempfile
from pathlib import Path
from support import LispyTestCase, lispy3


class LibraryImportTest(LispyTestCase):
    def setUp(self):
        super().setUp()
        lispy3.library_system.reset()
        self.macros = lispy3.macro_table.copy()
        lispy3.macro_table.clear()
        self.addCleanup(self.restore_macros)

    def restore_macros(self):
        lispy3.macro_table.clear()
        lispy3.macro_table.update(self.macros)

    def library(self, name='sample'):
        self.ev(f'''(define-library {name}
          (export add bump value)
          (begin
            (define value 10)
            (define (helper x) (+ x value))
            (define (add x) (helper x))
            (define-macro (bump x) `(helper ,x))))''')

    def test_only_import_keeps_helpers_private(self):
        self.library()
        self.ev('(import (only sample add))')
        self.assertEqual(self.ev('(add 3)'), 13)
        for name in ('helper', 'value'):
            with self.assertRaises(NameError):
                self.ev(name)
        self.assertNotIn('bump', lispy3.macro_table)

    def test_prefix_rename_and_composition(self):
        self.library()
        self.ev('(import (prefix (rename (only sample add) (add plus)) lib:))')
        self.assertEqual(self.ev('(lib:plus 5)'), 15)
        with self.assertRaises(NameError):
            self.ev('add')

    def test_imported_macro_keeps_helper_but_uses_caller_argument(self):
        self.library()
        self.ev('(define (helper x) (* x 100))')
        self.ev('(import (rename (only sample bump) (bump inc)))')
        self.assertEqual(self.ev('(let [value 5] (inc value))'), 15)
        self.assertEqual(self.ev('(inc (helper 2))'), 210)
        self.assertEqual(self.ev('(helper 2)'), 200)

    def test_macro_assignment_keeps_private_state(self):
        self.ev('''(define-library counter
          (export next count)
          (begin (define count 0)
            (define-macro (next) '(begin (set! count (+ count 1)) count))))''')
        self.ev('(import (prefix counter c:))')
        self.ev('(define count 100)')
        self.assertEqual(self.ev('(c:next)'), 1)
        self.assertEqual(self.ev('(c:next)'), 2)
        self.assertEqual(self.ev('c:count'), 2)
        self.assertEqual(self.ev('count'), 100)

    def test_macro_quotes_are_data_and_binding_names_stay_local(self):
        self.ev('''(define-library syntax-demo (export local quote-helper)
          (begin (define helper 99)
            (define-macro (local x) `(let [helper ,x] (+ helper 1)))
            (define-macro (quote-helper) '(quote helper))))''')
        self.ev('(import syntax-demo)')
        self.assertEqual(self.ev('(local 4)'), 5)
        self.assertEqual(self.ev('(quote-helper)'), 'helper')

    def test_libraries_with_same_private_names_do_not_conflict(self):
        self.library('first')
        self.ev('''(define-library second (export add)
          (begin (define (helper x) (* x 2)) (define (add x) (helper x))))''')
        self.ev('(import (prefix first a:) (prefix second b:))')
        self.assertEqual(self.ev('(list (a:add 2) (b:add 2))'), [12, 4])

    def test_nested_library_import_and_macro_dependency(self):
        self.library()
        self.ev('''(define-library client (export use)
          (import (only sample bump))
          (begin (define (use x) (bump x))))''')
        self.ev('(import client)')
        self.assertEqual(self.ev('(use 7)'), 17)
        self.assertNotIn('bump', lispy3.macro_table)

    def test_begin_import_then_call(self):
        self.library()
        self.assertEqual(self.ev('(begin (import (only sample bump)) (bump 2))'), 12)

    def test_import_errors_do_not_install_partial_bindings(self):
        self.library()
        self.ev('(define add 99)')
        with self.assertRaisesRegex(Exception, 'import.*add|collision.*add'):
            self.ev('(import sample)')
        self.assertEqual(self.ev('add'), 99)
        with self.assertRaises(NameError):
            self.ev('value')
        with self.assertRaisesRegex(Exception, 'export.*missing|missing.*export'):
            self.ev('(import (only sample missing))')

    def test_bad_library_does_not_publish_macros_or_registry(self):
        with self.assertRaisesRegex(Exception, 'export.*missing|missing.*export'):
            self.ev('''(define-library broken (export missing)
              (begin (define-macro (leak) 1)))''')
        self.assertNotIn('leak', lispy3.macro_table)
        self.ev('(define-library broken (export ok) (begin (define ok 42)))')
        self.ev('(import broken)')
        self.assertEqual(self.ev('ok'), 42)

    def test_imported_values_are_read_only_live_bindings(self):
        self.library()
        self.ev('(import (only sample value))')
        with self.assertRaisesRegex(Exception, 'import.*read.only|read.only.*import'):
            self.ev('(set! value 7)')
        self.assertEqual(self.ev('value'), 10)

    def test_file_library_and_include_are_relative(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'body.lisp').write_text('(define answer 42)', encoding='utf-8')
            path = root/'filedemo.sld'
            path.write_text('(define-library filedemo (export answer) (include "body.lisp"))', encoding='utf-8')
            self.ev('(import "'+path.as_posix()+'")')
            self.assertEqual(self.ev('answer'), 42)

    def test_selective_mini_basic_terminal_macro(self):
        self.ev('(import (prefix (only mini-basic CLS COLOUR ANSI ANSI-RESET) term:))')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(begin (term:CLS) (term:COLOUR 1) (term:ANSI 27 "[32m") (term:ANSI-RESET))')
        self.assertEqual(out.getvalue(), '\x1b[2J\x1b[H\x1b[31m\x1b[32m\x1b[0m')
        self.assertNotIn('bbc-cls', lispy3.global_env)
        self.assertNotIn('PRINT', lispy3.macro_table)

    def test_selective_mini_basic_reader_macro(self):
        self.ev('(import (only mini-basic bbc-run))')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-run "PRINT 42")')
        self.assertEqual(out.getvalue(), '        42\n')
        self.assertNotIn('bbc-print-value', lispy3.global_env)

    def test_nested_macro_keeps_callers_private_named_variable(self):
        self.library()
        self.ev('(import (only sample bump))')
        self.assertEqual(self.ev('(let [value 3] (bump (bump value)))'), 23)

    def test_mini_basic_source_variable_uses_caller_scope(self):
        self.ev('(import (only mini-basic bbc-run))')
        self.ev('(define source "PRINT 7")')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-run source)')
        self.assertEqual(out.getvalue(), '         7\n')

    def test_prefixed_reader_handles_loops_subroutines_and_functions(self):
        self.ev('(import (prefix (only mini-basic bbc-run) b:))')
        source = '10 FOR i=1 TO 2:GOSUB 100:NEXT:END\n100 PRINT ;FNdouble(i):RETURN\nDEF FNdouble(x)\n=x*2'
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(b:bbc-run """'+source+'\n""")')
        self.assertEqual(out.getvalue(), '2\n4\n')

    def test_macro_arguments_keep_core_special_forms(self):
        self.library()
        self.ev('(import (only sample bump))')
        self.assertEqual(self.ev('(bump (if #t 2 100))'), 12)

    def test_relative_private_method_macro(self):
        self.ev('''(define-library textlib (export shout)
          (begin (define message "hello") (define-macro (shout) '(message/upper))))''')
        self.ev('(import textlib)')
        self.assertEqual(self.ev('(shout)').value, 'HELLO')

    def test_repeated_import_does_not_reinitialize_state(self):
        self.ev('''(define-library stateful (export next)
          (begin (define n 0) (define (next) (set! n (+ n 1)) n)))''')
        self.ev('(import stateful)')
        self.assertEqual(self.ev('(next)'), 1)
        self.ev('(import stateful)')
        self.assertEqual(self.ev('(next)'), 2)

    def test_export_rename_and_macro_reexport(self):
        self.library()
        self.ev('''(define-library facade (export (rename bump more))
          (import (only sample bump)))''')
        self.ev('(import facade)')
        self.assertEqual(self.ev('(more 5)'), 15)

    def test_import_is_top_level_and_missing_names_are_clear(self):
        with self.assertRaisesRegex(SyntaxError, 'top-level'):
            self.ev('(lambda () (import unknown))')
        with self.assertRaisesRegex(Exception, 'library not found'):
            self.ev('(import does-not-exist)')

    def test_cyclic_file_import_reports_error_without_leaking(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cycle.sld'
            source = '(define-library cycle (import "'+path.as_posix()+'"))'
            path.write_text(source, encoding='utf-8')
            with self.assertRaisesRegex(Exception, 'cyclic library import'):
                self.ev('(import "'+path.as_posix()+'")')
            self.assertNotIn('cycle', lispy3.library_system.registry)

    def test_save_rejects_imports_before_writing_unreadable_bindings(self):
        self.library()
        self.ev('(import (only sample add))')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'workspace.lisp'
            with self.assertRaisesRegex(Exception, 'save.*import'):
                lispy3.save_workspace(str(path))
            self.assertFalse(path.exists())

    def test_imported_binding_cannot_be_redefined(self):
        self.library()
        self.ev('(import (only sample value))')
        with self.assertRaisesRegex(Exception, 'import.*read.only'):
            self.ev('(define value 30)')
        self.assertEqual(self.ev('value'), 10)

    def test_builtin_name_collision_can_be_resolved_with_prefix(self):
        self.ev('(define-library numbers (export +) (begin (define (+ x) x)))')
        with self.assertRaisesRegex(Exception, 'collision'):
            self.ev('(import numbers)')
        self.ev('(import (prefix numbers num:))')
        self.assertEqual(self.ev('(num:+ 7)'), 7)

    def test_rename_checks_collisions_before_installing(self):
        self.library()
        with self.assertRaisesRegex(Exception, 'collision'):
            self.ev('(import (rename sample (add value)))')
        self.assertNotIn('bump', lispy3.macro_table)
        self.assertNotIn('value', lispy3.global_env)

    def test_relative_library_dependency_uses_defining_file_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'dep.sld').write_text('(define-library dep (export x) (begin (define x 42)))', encoding='utf-8')
            path = root/'parent.sld'
            path.write_text('(define-library parent (export x) (import "dep.sld"))', encoding='utf-8')
            self.ev('(import "'+path.as_posix()+'")')
            self.assertEqual(self.ev('x'), 42)

    def test_same_library_name_in_different_files_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for filename, value in [('one.sld', 1), ('two.sld', 2)]:
                (root/filename).write_text(f'(define-library duplicate (export x) (begin (define x {value})))', encoding='utf-8')
            self.ev('(import "'+(root/'one.sld').as_posix()+'")')
            self.ev('(import "'+(root/'one.sld').as_posix()+'")')
            with self.assertRaisesRegex(Exception, 'already defined'):
                self.ev('(import "'+(root/'two.sld').as_posix()+'")')
            self.assertEqual(self.ev('x'), 1)

    def test_library_read_and_eval_keep_private_macro_scope(self):
        self.ev('''(define-library reader-lib (export run)
          (begin (define-macro (private-m) 7)
            (define (run) (eval (read "(private-m)")))))''')
        self.ev('(define-macro (private-m) 99)')
        self.ev('(import reader-lib)')
        self.assertEqual(self.ev('(run)'), 7)
