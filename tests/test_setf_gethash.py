"""Common Lisp hash-table places used by manual memoization examples."""
import contextlib
import io
from support import LispyTestCase, lispy3 as L


class HashPlaceTest(LispyTestCase):
    def test_insert_overwrite_default_and_assigned_value(self):
        self.ev('(define table (make-hash-table))')
        self.assertEqual(self.ev('(gethash 1 table)'), [])
        self.assertEqual(self.ev('(gethash 1 table 99)'), 99)
        self.assertEqual(self.ev('(setf (gethash 1 table) 10)'), 10)
        self.assertEqual(self.ev('(setf (gethash 1 table) 20)'), 20)
        self.assertEqual(self.ev('(gethash 1 table)'), 20)

    def test_stored_false_and_zero_do_not_use_default(self):
        self.ev('(define table (make-hash-table))')
        self.ev('(setf (gethash 0 table) 0 (gethash 1 table) nil)')
        self.assertEqual(self.ev('(gethash 0 table 99)'), 0)
        self.assertEqual(self.ev('(gethash 1 table 99)'), [])

    def test_mixed_places_are_sequential_and_return_last_value(self):
        self.ev('(define table (make-hash-table))')
        self.ev('(define x 0)')
        self.assertEqual(self.ev('(setf x 7 (gethash x table) (+ x 1) x (gethash 7 table))'), 8)
        self.assertEqual(self.ev('x'), 8)

    def test_place_and_value_are_evaluated_once_in_order(self):
        self.ev('(define table (make-hash-table))')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(self.ev('(setf (gethash (begin (display "K") 1) (begin (display "T") table) (begin (display "D") 0)) (begin (display "V") 42))'), 42)
        self.assertEqual(out.getvalue().splitlines(), ['K', 'T', 'D', 'V'])
        self.assertEqual(self.ev('(gethash 1 table)'), 42)

    def test_table_reference_is_captured_before_value_runs(self):
        self.ev('(define table (make-hash-table))')
        self.ev('(define original table)')
        self.ev('(setf (gethash 1 table) (begin (set! table (make-hash-table)) 42))')
        self.assertEqual(self.ev('(gethash 1 original)'), 42)
        self.assertEqual(self.ev('(gethash 1 table)'), [])

    def test_book_fibonacci_closure_caches_results(self):
        self.ev('(define calls 0)')
        self.ev("""(let ((memo (make-hash-table)))
          (defun fibonacci (n)
            (incf calls)
            (let ((value (gethash n memo)))
              (cond ((<= n 1) n)
                    (value value)
                    (t (setf (gethash n memo)
                         (+ (fibonacci (- n 1)) (fibonacci (- n 2)))))))))""")
        self.assertEqual(self.ev('(fibonacci 40)'), 102334155)
        count = self.ev('calls')
        self.assertLess(count, 100)
        self.assertEqual(self.ev('(fibonacci 40)'), 102334155)
        self.assertEqual(self.ev('calls'), count + 1)

    def test_unsupported_places_and_bad_arity_still_error(self):
        for source in ('(setf (car x) 1)', '(setf (gethash 1) 2)', '(setf (gethash 1 t 2 3) 4)', '(setf x)'):
            with self.subTest(source=source), self.assertRaises(SyntaxError):
                self.ev(source)

    def test_non_table_is_rejected(self):
        with self.assertRaises(TypeError):
            self.ev('(gethash 1 2)')
        with self.assertRaises(TypeError):
            self.ev('(setf (gethash 1 2) 3)')
