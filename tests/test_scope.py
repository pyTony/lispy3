"""Tests for variable scope: where a name is visible and which binding it means.

Each test's docstring says what it covers. To see them one by one, run from
the repository folder:

    python -m unittest -v tests.test_scope
"""
import unittest

from support import LispyTestCase


class ClosureTest(LispyTestCase):
    """A function made inside another keeps the variables it was made with."""

    def test_counters_keep_separate_state(self):
        """Two counters from the same maker each count on their own."""
        self.ev("(define (make-counter) (let ((n 0)) (lambda () (set! n (+ n 1)) n)))")
        self.ev_all("(define c1 (make-counter))", "(define c2 (make-counter))")
        self.assertEqual([self.ev("(c1)"), self.ev("(c1)"), self.ev("(c2)")], [1, 2, 1])

    def test_closure_ignores_a_later_global_of_the_same_name(self):
        """make-adder's k stays 5 even after a global k is defined."""
        self.ev_all("(define (make-adder k) (lambda (x) (+ x k)))",
                    "(define add5 (make-adder 5))", "(define k 100)")
        self.assertEqual(self.ev("(add5 1)"), 6)

    def test_closures_made_in_dotimes_keep_their_own_i(self):
        """Each pass of dotimes gets a fresh i, as in Clojure, so the lambdas see 2, 1, 0."""
        self.ev_all("(define fs (list))",
                    "(dotimes (i 3) (set! fs (cons (lambda () i) fs)))")
        self.assertEqual(self.ev("(map (lambda (f) (f)) fs)"), [2, 1, 0])


class NoLeakTest(LispyTestCase):
    """Local names disappear when their form ends."""

    def assertUndefined(self, name):
        with self.assertRaises(NameError):
            self.ev(name)

    def test_let_binding(self):
        """A let variable is gone after the let."""
        self.assertEqual(self.ev("(let ((zz 1)) zz)"), 1)
        self.assertUndefined("zz")

    def test_lambda_parameter(self):
        """A parameter is gone after the call."""
        self.assertEqual(self.ev("((lambda (pp) pp) 1)"), 1)
        self.assertUndefined("pp")

    def test_dotimes_variable(self):
        """The dotimes counter is gone after the loop."""
        self.ev("(dotimes (ii 3) ii)")
        self.assertUndefined("ii")

    def test_define_inside_a_function(self):
        """A define in a function body stays inside the function."""
        self.ev("(define (f) (define secret 1) secret)")
        self.assertEqual(self.ev("(f)"), 1)
        self.assertUndefined("secret")

    def test_define_inside_a_let(self):
        """A define in a let body stays inside the let."""
        self.assertEqual(self.ev("(let ((a 1)) (define inside 2) (+ a inside))"), 3)
        self.assertUndefined("inside")


class ShadowingTest(LispyTestCase):
    """An inner name hides an outer one without changing it."""

    def test_let_shadows_a_global(self):
        """(let ((x 1)) x) is 1, and the global x is still 10 afterwards."""
        self.ev("(define x 10)")
        self.assertEqual(self.ev("(let ((x 1)) x)"), 1)
        self.assertEqual(self.ev("x"), 10)

    def test_set_on_a_parameter_stays_local(self):
        """set! on a parameter named like a global changes only the parameter."""
        self.ev_all("(define w 1)", "(define (g w) (set! w 99) w)")
        self.assertEqual(self.ev("(g 5)"), 99)
        self.assertEqual(self.ev("w"), 1)

    def test_inner_define_does_not_overwrite_a_global(self):
        """A define inside a function makes a new local name, the global keeps its value."""
        self.ev_all("(define gg 1)", "(define (setg) (define gg 2) gg)")
        self.assertEqual(self.ev("(setg)"), 2)
        self.assertEqual(self.ev("gg"), 1)

    def test_set_in_a_function_changes_the_global(self):
        """set! of a name the function doesn't bind changes the outer variable."""
        self.ev_all("(define y 1)", "(define (bump) (set! y (+ y 1)))", "(bump)")
        self.assertEqual(self.ev("y"), 2)

    def test_let_bindings_do_not_see_each_other(self):
        """In (let ((a 2) (b a)) ...), b gets the outer a, not the new one."""
        self.assertEqual(self.ev("(let ((a 1)) (let ((a 2) (b a)) b))"), 1)


class LexicalScopeTest(LispyTestCase):
    """Names are looked up where a function was written, not where it is called."""

    def test_scope_is_lexical_not_dynamic(self):
        """getq sees the global q, not the q of the function that calls it."""
        self.ev_all("(define q 1)", "(define (getq) q)", "(define (h q) (getq))")
        self.assertEqual(self.ev("(h 2)"), 1)

    def test_recursive_inner_define(self):
        """An inner helper function can call itself."""
        self.ev("(define (outer n) (define (loop i acc) (if (= i 0) acc (loop (- i 1) (* acc i))))"
                " (loop n 1))")
        self.assertEqual(self.ev("(outer 5)"), 120)

    def test_mutually_recursive_inner_defines(self):
        """Two inner helpers can call each other, whichever is defined first."""
        self.ev("(define (pe n) (define (e? n) (if (= n 0) #t (o? (- n 1))))"
                " (define (o? n) (if (= n 0) #f (e? (- n 1)))) (e? n))")
        self.assertIs(self.ev("(pe 10)"), True)

    def test_gensym_macro_does_not_capture_the_callers_variable(self):
        """A macro's gensym temporary can't clash with a caller's variable named tmp."""
        self.ev("(define-macro (my-or2 a b) (let [tmp (gensym)] `(let [,tmp ,a] (if ,tmp ,tmp ,b))))")
        self.ev("(define tmp 5)")
        self.assertEqual(self.ev("(my-or2 #f tmp)"), 5)


if __name__ == "__main__":
    unittest.main()
