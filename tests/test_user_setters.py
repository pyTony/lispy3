"""Common Lisp (defun (setf accessor) ...) support."""
import contextlib
import io
from support import LispyTestCase, lispy3 as L


class UserSetterTest(LispyTestCase):
    def test_book_square_area(self):
        self.ev('(defparameter *square* (make-hash-table))')
        self.ev('(setf (gethash :width *square*) 21)')
        self.ev('(defun area (square) (expt (gethash :width square) 2))')
        self.ev('(defun (setf area) (new-area square) (let ((width (sqrt new-area))) (setf (gethash :width square) width)))')
        self.assertEqual(self.ev('(area *square*)'), 441)
        # The storing function returns its own final value (width here).
        self.assertEqual(self.ev('(setf (area *square*) 100)'), 10)
        self.assertEqual(self.ev('(gethash :width *square*)'), 10)
        self.assertEqual(self.ev('(area *square*)'), 100)
        self.assertNotIn('setf', L.global_env)

    def test_evaluation_order_once_and_value_argument_first(self):
        self.ev('(define table (make-hash-table))')
        self.ev('(defun (setf entry) (value key table) (setf (gethash key table) value))')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = self.ev('(setf (entry (begin (display "K") 7) (begin (display "T") table)) (begin (display "V") 42))')
        self.assertEqual(out.getvalue().splitlines(), ['K', 'T', 'V'])
        self.assertEqual(result, 42)
        self.assertEqual(self.ev('(gethash 7 table)'), 42)

    def test_setter_closes_over_local_state_and_redefinition_works(self):
        self.ev('(let ((table (make-hash-table))) (defun hidden (key) (gethash key table)) (defun (setf hidden) (value key) (setf (gethash key table) value)))')
        self.assertEqual(self.ev('(setf (hidden 1) 9)'), 9)
        self.assertEqual(self.ev('(hidden 1)'), 9)
        self.ev('(defun (setf hidden) (value key) (+ value 1))')
        self.assertEqual(self.ev('(setf (hidden 1) 9)'), 10)
        self.assertEqual(self.ev('(hidden 1)'), 9)

    def test_multiple_pairs_and_optional_arguments(self):
        self.ev('(define table (make-hash-table))')
        self.ev('(define x 0)')
        self.ev('(defun (setf field) (value &optional (key 1)) (setf (gethash key table) value))')
        self.assertEqual(self.ev('(setf (field) 4 x (gethash 1 table) (field 2) (+ x 1))'), 5)
        self.assertEqual(self.ev('(gethash 2 table)'), 5)

    def test_unknown_setter_and_invalid_defun_names_report_errors(self):
        with self.assertRaisesRegex(SyntaxError, 'setter'):
            self.ev('(setf (unknown-place 1) 2)')
        for source in ('(defun (wrong area) (v) v)', '(defun (setf) (v) v)', '(defun (setf area extra) (v) v)', '(defun (setf area) () 1)', '(defun 12 (v) v)'):
            with self.subTest(source=source), self.assertRaises(SyntaxError):
                self.ev(source)

    def test_setter_parameter_arity_is_checked(self):
        self.ev('(defun (setf field) (value object) value)')
        with self.assertRaises(TypeError):
            self.ev('(setf (field) 2)')
