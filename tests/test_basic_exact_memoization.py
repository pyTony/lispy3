"""Automatic BASIC caches depend on argument values, not return types."""
from fractions import Fraction
from unittest import TestCase
from unittest.mock import patch
from support import LispyTestCase, lispy3


class ExactArgumentMemoTest(TestCase):
    def test_only_exact_numeric_arguments_use_cache(self):
        calls = []
        def function(*args):
            calls.append(args)
            return 0.5
        memo = lispy3.memoize(function, exact_arguments_only=True)
        for args in [(1,), (Fraction(1, 2),), (2, Fraction(3, 2)), ()]:
            with self.subTest(args=args):
                before = len(calls)
                self.assertEqual(memo(*args), 0.5)
                self.assertEqual(memo(*args), 0.5)
                self.assertEqual(len(calls)-before, 1)
        # In particular 1.0 must not hit the cached key for integer 1.
        for args in [(1.0,), (1, 2.0), ('text',), (True,), (1+0j,), ([1],)]:
            with self.subTest(args=args):
                before = len(calls)
                memo(*args)
                memo(*args)
                self.assertEqual(len(calls)-before, 2)

    def test_explicit_memoize_still_caches_floats(self):
        calls = []
        memo = lispy3.memoize(lambda x: calls.append(x) or x)
        memo(0.25)
        memo(0.25)
        self.assertEqual(calls, [0.25])


class BasicMemoIntegrationTest(LispyTestCase):
    def tearDown(self):
        lispy3.library_system.reset()

    def test_lisp_define_memo_gates_actual_argument_types(self):
        self.ev('(define calls 0)')
        self.ev('(define-memo (f x) (set! calls (+ calls 1)) 0.5)')
        for source in ['(f 1)', '(f 1)', '(f 1.0)', '(f 1.0)', '(f 1/2)', '(f 1/2)']:
            self.assertEqual(self.ev(source), 0.5)
        self.assertEqual(self.ev('calls'), 4)

    def test_reader_memoizes_integer_calls_but_not_float_calls(self):
        self.ev('(import (only mini-basic bbc-run))')
        actual = lispy3.memoize
        calls = []
        def factory(proc, **kwargs):
            def counted(*args):
                calls.append(args)
                return proc(*args)
            return actual(counted, **kwargs)
        with patch.object(lispy3, 'memoize', side_effect=factory):
            self.ev('(bbc-run "DEF FNdouble(n) = n*2")')
        self.ev('(bbc-run "A=FNdouble(1):B=FNdouble(1):C=FNdouble(1.0):D=FNdouble(1.0)")')
        self.assertEqual(calls, [(1,), (1.0,), (1.0,)])

    def test_recursive_lisp_factorial_reuses_exact_calls(self):
        from math import factorial
        self.ev('(define body-calls 0)')
        self.ev('(define-memo (fact n) (set! body-calls (+ body-calls 1)) (if (< n 2) 1 (* n (fact (- n 1)))))')
        self.assertEqual(self.ev('(fact 60)'), factorial(60))
        self.assertEqual(self.ev('body-calls'), 60)
        self.assertEqual(self.ev('(fact 60)'), factorial(60))
        self.assertEqual(self.ev('body-calls'), 60)
        self.assertEqual(self.ev('(fact 59)'), factorial(59))
        self.assertEqual(self.ev('body-calls'), 60)
