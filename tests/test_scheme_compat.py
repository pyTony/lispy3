"""Tests for the places where Lispy now agrees with Scheme.

A comparison with GNU Guile (October 2026) found Lispy giving different
answers for truth tests, vectors, dotted pairs, sort, Scheme-style let and
division. Each class below covers one of them. Run from the repository folder:

    python -m unittest discover tests
"""
import os
import tempfile
import unittest

from support import LispyTestCase, lispy3


class TruthTest(LispyTestCase):

    def test_zero_is_true(self):
        """0 and 0.0 are true, as in every Lisp."""
        self.assertEqual(self.show("(if 0 'yes 'no)"), "yes")
        self.assertEqual(self.show("(if 0.0 'yes 'no)"), "yes")
        self.assertIs(self.ev("(not 0)"), False)
        self.assertEqual(self.ev("(and 1 0 3)"), 3)
        self.assertEqual(self.ev("(or #f 0 7)"), 0)

    def test_only_false_and_empty_list_are_false(self):
        """Only #f and () are false."""
        self.assertEqual(self.show("(if #f 'yes 'no)"), "no")
        self.assertEqual(self.show("(if '() 'yes 'no)"), "no")
        self.assertIs(self.ev("(not '())"), True)
        self.assertEqual(self.show("(cond (0 'zero) (else 'other))"), "zero")

    def test_empty_vector_and_string_are_true(self):
        """An empty vector and an empty string are true."""
        self.assertEqual(self.show("(if [] 'yes 'no)"), "yes")
        self.assertEqual(self.show("(if \"\" 'yes 'no)"), "yes")

    def test_while_and_filter_use_lisp_truth(self):
        """while and filter use the same truth rules, so 0 counts as true."""
        self.assertEqual(self.show("(filter (lambda (x) x) (list 0 #f 1 '()))"), "(0 1)")
        self.ev_all("(define n 0)", "(define flag 0)",
                    "(while flag (set! n (+ n 1)) (if (= n 3) (set! flag #f) 0))")
        self.assertEqual(self.ev("n"), 3)


class VectorTest(LispyTestCase):

    def test_vectors_are_vectors(self):
        """Every way of making a vector gives something vector? accepts and list? does not."""
        for source in ("(vector 1 2)", "(make-vector 2 0)", "[1 2]", "(list->vector '(1 2))"):
            with self.subTest(source=source):
                self.assertIs(self.ev(f"(vector? {source})"), True)
                self.assertIs(self.ev(f"(list? {source})"), False)
        self.assertIs(self.ev("(vector? '(1 2))"), False)

    def test_vectors_print_with_brackets(self):
        """Vectors print with [ ]."""
        self.assertEqual(self.show("(vector 1 (+ 1 1) 3)"), "[1 2 3]")
        self.assertEqual(self.show("(let ((v (make-vector 2 0))) (vector-set! v 0 9) v)"), "[9 0]")

    def test_vector_length_and_conversions(self):
        """vector-length, vector->list, and an empty vector is not null?."""
        self.assertEqual(self.ev("(vector-length (vector 1 2 3))"), 3)
        self.assertEqual(self.show("(vector->list [1 2])"), "(1 2)")
        self.assertIs(self.ev("(null? [])"), False)


class PairTest(LispyTestCase):

    def test_cons_onto_a_non_list_makes_a_pair(self):
        """(cons 1 2) makes the dotted pair (1 . 2)."""
        self.assertEqual(self.show("(cons 1 2)"), "(1 . 2)")
        self.assertEqual(self.show("(cons 1 (cons 2 3))"), "(1 2 . 3)")
        self.assertEqual(self.show("(cons 1 '(2 3))"), "(1 2 3)")

    def test_quoted_dotted_pairs(self):
        """Quoted dotted pairs read correctly, and car and cdr take them apart."""
        self.assertEqual(self.ev("(car '(1 . 2))"), 1)
        self.assertEqual(self.ev("(cdr '(1 . 2))"), 2)
        self.assertEqual(self.show("(cdr '(a b . c))"), "(b . c)")
        self.assertEqual(self.show("'(1 . (2 3))"), "(1 2 3)")
        self.assertEqual(self.show("'((a . 1) (b . 2))"), "((a . 1) (b . 2))")

    def test_pair_predicates(self):
        """pair? is true for pairs and non-empty lists; a dotted pair is not a list?."""
        self.assertIs(self.ev("(pair? '(1 . 2))"), True)
        self.assertIs(self.ev("(pair? '(1))"), True)
        self.assertIs(self.ev("(pair? '())"), False)
        self.assertIs(self.ev("(list? '(1 . 2))"), False)
        self.assertIs(self.ev("(equal? (cons 1 2) '(1 . 2))"), True)

    def test_a_pair_has_no_length(self):
        """length of a dotted pair is an error."""
        with self.assertRaises(TypeError):
            self.ev("(length '(1 . 2))")

    def test_dotted_parameters_still_work(self):
        """(lambda (a . rest) ...) still collects the extra arguments."""
        self.assertEqual(self.show("((lambda (a . rest) rest) 1 2 3)"), "(2 3)")
        self.ev("(define (f a . rest) (list a rest))")
        self.assertEqual(self.show("(f 1 2 3)"), "(1 (2 3))")


class SortTest(LispyTestCase):

    def test_a_comparison_that_fails_is_an_error(self):
        """Sorting strings with < is an error instead of a silently unsorted list."""
        with self.assertRaises(TypeError):
            self.ev("(sort '(\"b\" \"a\") <)")

    def test_comparisons_and_key_functions(self):
        """sort takes a two-argument comparison or a one-argument key function."""
        self.assertEqual(self.show("(sort '(3 1 2) <)"), "(1 2 3)")
        self.assertEqual(self.show("(sort '(3 1 2) >)"), "(3 2 1)")
        self.assertEqual(self.show("(sort '(-3 1 -2) abs)"), "(1 -2 -3)")
        self.assertEqual(self.show("(sort '(-3 1 -2) (lambda (x) (- x)))"), "(1 -2 -3)")
        self.assertEqual(self.show("(sort '(3 1 2) (lambda (a b) (< a b)))"), "(1 2 3)")


class SchemeLetTest(LispyTestCase):

    def test_scheme_style_let(self):
        """Scheme's (let ((a 1) (b 2)) ...) works."""
        self.assertEqual(self.ev("(let ((a 1) (b 2)) (+ a b))"), 3)
        self.assertEqual(self.ev("(let ((a 1)) a)"), 1)

    def test_scheme_let_values_use_the_outer_names(self):
        """In a Scheme let, the values see the outer names, not the new ones."""
        self.ev("(define x 1)")
        self.assertEqual(self.show("(let ((x 10) (y x)) (list x y))"), "(10 1)")

    def test_lispy_style_let_is_unchanged(self):
        """Lispy's own (let [a 1 b (+ a 1)] ...) still works."""
        self.assertEqual(self.ev("(let [a 1 b (+ a 1)] b)"), 2)
        self.assertEqual(self.show("(let [p (list 1 2)] p)"), "(1 2)")

    def test_named_let_loops_without_using_the_stack(self):
        """A named let loops 100000 times without a stack overflow."""
        self.assertEqual(self.show(
            "(let loop ((i 0) (acc '())) (if (= i 3) acc (loop (+ i 1) (cons i acc))))"), "(2 1 0)")
        self.assertEqual(self.show("(let loop ((i 0)) (if (= i 100000) 'done (loop (+ i 1))))"), "done")

    def test_odd_lispy_bindings_say_how_to_write_let(self):
        """A let with a name but no value explains how to write let."""
        with self.assertRaisesRegex(SyntaxError, r"\(let \[a 1 b 2\]"):
            self.ev("(let [a 1 b] a)")


class FractionTest(LispyTestCase):

    def test_whole_numbers_divide_exactly(self):
        """Dividing whole numbers gives an exact fraction, or a whole number."""
        self.assertEqual(self.show("(/ 7 2)"), "7/2")
        self.assertEqual(self.show("(/ 1 3)"), "1/3")
        self.assertEqual(self.show("(/ 2)"), "1/2")
        self.assertEqual(self.show("(/ 6 3)"), "2")
        self.assertIs(type(self.ev("(/ 6 3)")), int)

    def test_decimals_stay_decimal(self):
        """Dividing a decimal gives a decimal."""
        self.assertEqual(self.show("(/ 7.0 2)"), "3.5")
        self.assertEqual(self.show("(exact->inexact 1/3)"), "0.3333333333333333")

    def test_fraction_literals_and_arithmetic(self):
        """1/3 is a number you can type, add, multiply and compare."""
        self.assertEqual(self.show("(+ 1/3 1/6)"), "1/2")
        self.assertEqual(self.show("(* 2/3 3/2)"), "1")
        self.assertEqual(self.show("-3/4"), "-3/4")
        self.assertEqual(self.show("(expt 2 -1)"), "1/2")
        self.assertEqual(self.show("(string->number \"1/2\")"), "1/2")
        self.assertIs(self.ev("(< 1/3 0.34)"), True)

    def test_fraction_helpers(self):
        """numerator, denominator, exact, exact? and integer? on fractions."""
        self.assertEqual(self.ev("(numerator 6/4)"), 3)
        self.assertEqual(self.ev("(denominator 6/4)"), 2)
        self.assertEqual(self.show("(exact 2.5)"), "5/2")
        self.assertIs(self.ev("(exact? 1/2)"), True)
        self.assertIs(self.ev("(number? 1/2)"), True)
        self.assertIs(self.ev("(integer? 1/2)"), False)
        self.assertEqual(self.ev("(floor 7/2)"), 3)
        self.assertEqual(self.ev("(round 7/2)"), 4)

    def test_remainders_of_fractions_are_simplified(self):
        """mod, remainder and divmod on fractions stay exact and give 0, not 0/1."""
        self.assertIs(type(self.ev("(mod 3/2 1/2)")), int)
        self.assertIs(self.ev("(integer? (mod 3/2 1/2))"), True)
        self.assertEqual(self.show("(divmod 3 1/2)"), "(6 0)")
        self.assertEqual(self.show("(remainder 3/2 1/2)"), "0")
        self.assertEqual(self.show("(remainder -7/2 1)"), "-1/2")
        self.assertEqual(self.show("(quotient -7/2 1)"), "-3")
        self.assertEqual(self.show("(remainder 7.5 2)"), "1.5")

    def test_exact_reads_a_decimal_as_printed(self):
        """(exact 0.1) is 1/10, the simplest fraction for the decimal as it prints."""
        self.assertEqual(self.show("(exact 0.1)"), "1/10")
        self.assertEqual(self.show("(exact -0.75)"), "-3/4")
        self.assertEqual(self.show("(inexact->exact 3.0)"), "3")

    def test_division_by_zero(self):
        """(/ 1 0) is an error."""
        with self.assertRaises(ZeroDivisionError):
            self.ev("(/ 1 0)")

    def test_a_name_with_a_slash_is_still_a_method_call(self):
        """s/upper is still a method call, not a fraction."""
        self.ev('(define s "abc")')
        self.assertEqual(self.show("(s/upper)"), '"ABC"')


class SaveTest(LispyTestCase):

    def test_vectors_pairs_and_fractions_survive_save_and_load(self):
        """Vectors, pairs and fractions come back unchanged after save and load."""
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws").replace("\\", "/")
            self.ev_all("(define v (vector 'a 2))", "(define p (cons 1 2))", "(define f 7/2)")
            self.ev(f'(save "{name}")')
            lispy3.global_env.clear()
            lispy3.global_env.update(lispy3.standard_env())
            self.ev(f'(load "{name}")')
        self.assertEqual(self.show("v"), "[a 2]")
        self.ev("(vector-set! v 0 9)")
        self.assertEqual(self.show("v"), "[9 2]")
        self.assertEqual(self.show("p"), "(1 . 2)")
        self.assertEqual(self.show("f"), "7/2")


class ArgumentCountTest(LispyTestCase):

    def test_rest_parameters(self):
        """Rest parameters get () when there are no extra arguments, also through apply."""
        self.assertEqual(self.show("((lambda args args))"), "()")
        self.assertEqual(self.show("((lambda (a . rest) rest) 1 2 3)"), "(2 3)")
        self.ev("(define (g a . xs) (list a xs))")
        self.assertEqual(self.show("(g 1)"), "(1 ())")
        self.assertEqual(self.show("(apply g 1 '(2 3))"), "(1 (2 3))")

    def test_too_few_arguments_is_an_error(self):
        """Too few arguments is an error naming the function and the counts."""
        with self.assertRaisesRegex(TypeError, "takes 2 arguments, got 1"):
            self.ev("((lambda (a b) (+ a b)) 1)")
        self.ev("(define (g a b . xs) xs)")
        with self.assertRaisesRegex(TypeError, "g takes at least 2 arguments, got 1"):
            self.ev("(g 1)")

    def test_too_many_arguments_is_an_error(self):
        """Too many arguments is an error naming the function and the counts."""
        self.ev("(define (sq x) (* x x))")
        with self.assertRaisesRegex(TypeError, "sq takes 1 argument, got 2"):
            self.ev("(sq 1 2)")

    def test_min_and_max_of_one_value(self):
        """min and max work on a single value."""
        self.assertEqual(self.ev("(min 3)"), 3)
        self.assertEqual(self.ev("(max 3)"), 3)
        self.assertEqual(self.ev("(max 1 5 2)"), 5)


class StringAppendTest(LispyTestCase):

    def test_joins_strings(self):
        """string-append joins its strings."""
        self.assertEqual(self.show('(string-append "a" "b" "c")'), '"abc"')
        self.assertEqual(self.show('(string-append "solo")'), '"solo"')

    def test_no_strings_gives_the_empty_string(self):
        """(string-append) gives the empty string."""
        self.assertEqual(self.show("(string-append)"), '""')

    def test_only_strings(self):
        """string-append of a non-string is an error."""
        with self.assertRaisesRegex(TypeError, "string-append needs strings, got 1"):
            self.ev('(string-append "a" 1)')


if __name__ == "__main__":
    unittest.main()
