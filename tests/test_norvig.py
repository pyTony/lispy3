"""Regression tests from Peter Norvig's "(How to Write a (Lisp) Interpreter (in Python))".

https://norvig.com/lispy.html

Lispy started as a Python 3 version of Norvig's lis.py, so everything his page
shows should keep working. The examples are his, in his order, with his
expected results. Where Lispy behaves differently on purpose, the test says so
in a comment and checks Lispy's behaviour. Things his lis.py has and Lispy does
not have yet are in KnownGapsTest at the end: they are expected failures, so
the suite stays green, and they turn into "unexpected success" (a failure) once
the feature is added, as a reminder to move the test up.

The last group, NorvigLispyTestSuite, is the lis_tests list from Norvig's own
lispytest.py (also in https://github.com/fluentpython/lispy).
"""
import unittest

from support import LispyTestCase, lispy3


class ParsingTest(LispyTestCase):
    """Norvig's "Parsing: parse, tokenize and read_from_tokens" section."""

    program = "(begin (define r 10) (* pi (* r r)))"

    def test_tokenize(self):
        self.assertEqual(lispy3.tokenize(self.program),
                         ['(', 'begin', '(', 'define', 'r', '10', ')',
                          '(', '*', 'pi', '(', '*', 'r', 'r', ')', ')', ')'])

    def test_parse(self):
        self.assertEqual(lispy3.parse(self.program),
                         ['begin', ['define', 'r', 10], ['*', 'pi', ['*', 'r', 'r']]])

    def test_atoms(self):
        # Norvig: ints, then floats, else symbols
        self.assertEqual(lispy3.atom('10'), 10)
        self.assertIsInstance(lispy3.atom('10'), int)
        self.assertEqual(lispy3.atom('-3.14e159'), -3.14e159)
        self.assertIsInstance(lispy3.atom('2.0'), float)
        self.assertEqual(lispy3.atom('r'), 'r')
        self.assertIsInstance(lispy3.atom('r'), str)

    def test_nested_list(self):
        self.assertEqual(lispy3.parse("(quote (testing 1 (2.0) -3.14e159))"),
                         ['quote', ['testing', 1, [2.0], -3.14e159]])

    def test_extra_closing_bracket_is_an_error(self):
        # Norvig: read_from_tokens raises SyntaxError('unexpected )')
        with self.assertRaises(SyntaxError):
            lispy3.parse(")")

    def test_empty_input_is_an_error(self):
        # Norvig: SyntaxError('unexpected EOF')
        with self.assertRaises(SyntaxError):
            lispy3.parse("")

    def test_missing_closing_bracket(self):
        # Intentional difference: Norvig raises 'unexpected EOF' for "(+ 1 2";
        # Lispy closes the open brackets for you.
        self.assertEqual(lispy3.parse("(+ 1 (* 2 3"), ['+', 1, ['*', 2, 3]])


class EvalTest(LispyTestCase):
    """Norvig's "Evaluation: eval" section and its first program."""

    def test_program(self):
        self.assertAlmostEqual(self.ev("(begin (define r 10) (* pi (* r r)))"),
                               314.1592653589793)

    def test_variable_reference(self):
        self.ev("(define r 10)")
        self.assertEqual(self.ev("r"), 10)

    def test_undefined_variable(self):
        # Norvig: a KeyError from the dict lookup; Lispy names the symbol.
        with self.assertRaises(NameError):
            self.ev("undefined-thing")

    def test_constant_number(self):
        self.assertEqual(self.ev("12"), 12)
        self.assertEqual(self.ev("-2.5"), -2.5)

    def test_if_takes_then_branch(self):
        # Norvig: (if (> (* 11 11) 120) (* 7 6) oops) => 42, and oops is never looked up.
        self.assertEqual(self.ev("(if (> (* 11 11) 120) (* 7 6) oops)"), 42)

    def test_if_takes_else_branch(self):
        self.assertEqual(self.ev("(if (< (* 11 11) 120) oops (* 7 6))"), 42)

    def test_define_returns_nothing(self):
        # Nothing is printed after a define in Norvig's REPL or in Lispy's.
        self.assertIsNone(self.ev("(define r 10)"))

    def test_procedure_call(self):
        self.assertEqual(self.ev("(sqrt (* 2 8))"), 4.0)


class ReplTest(LispyTestCase):
    """Norvig's "Interaction: A REPL" section: what the REPL prints."""

    def test_repl_session(self):
        # lis.py> (define r 10)
        # lis.py> (* pi (* r r))
        # 314.159265359
        # lis.py> (if (> (* 11 11) 120) (* 7 6) oops)
        # 42
        # lis.py> (list (+ 1 1) (+ 2 2) (* 2 3) (expt 2 3))   -> see KnownGapsTest for expt
        self.ev("(define r 10)")
        self.assertEqual(self.show("(* pi (* r r))"), "314.1592653589793")
        self.assertEqual(self.show("(if (> (* 11 11) 120) (* 7 6) oops)"), "42")
        self.assertEqual(self.show("(list (+ 1 1) (+ 2 2) (* 2 3) (pow 2 3))"), "(2 4 6 8.0)")

    def test_lists_print_in_scheme_syntax(self):
        # Norvig's schemestr: a Python list is printed as (a b c)
        self.assertEqual(lispy3.lisp_str([1, ['a', 2.5], []]), "(1 (a 2.5) ())")

    def test_booleans_print_as_hash_t_and_hash_f(self):
        # Intentional difference: Norvig's lis.py prints True and False;
        # Lispy prints Scheme's #t and #f.
        self.assertEqual(self.show("(> 2 1)"), "#t")
        self.assertEqual(self.show("(< 2 1)"), "#f")

    def test_repl_prints_results_and_errors(self):
        import builtins
        import contextlib
        import io

        lines = iter(["(define r 10)", "(* pi (* r r))", "(car)", "exit"])
        out = io.StringIO()
        real_input = builtins.input
        builtins.input = lambda prompt='': next(lines)
        try:
            with contextlib.redirect_stdout(out):
                lispy3.repl()
        finally:
            builtins.input = real_input
        text = out.getvalue()
        self.assertIn("314.1592653589793", text)
        self.assertIn("Error:", text)        # the REPL survives an error
        self.assertIn("Goodbye!", text)


class LanguageTest(LispyTestCase):
    """Norvig's "Language 1: Lispy Calculator" and "Language 2: Full Lispy" examples."""

    def test_circle_area(self):
        self.ev("(define circle-area (lambda (r) (* pi (* r r))))")
        self.assertAlmostEqual(self.ev("(circle-area 3)"), 28.274333877)

    def test_factorial(self):
        self.ev("(define fact (lambda (n) (if (<= n 1) 1 (* n (fact (- n 1))))))")
        self.assertEqual(self.ev("(fact 10)"), 3628800)
        self.assertEqual(
            self.ev("(fact 100)"),
            93326215443944152681699238856266700490715968264381621468592963895217599993229915608941463976156518286253697920827223758251185210916864000000000000000000000000)

    def test_circle_area_of_factorial(self):
        self.ev_all("(define circle-area (lambda (r) (* pi (* r r))))",
                    "(define fact (lambda (n) (if (<= n 1) 1 (* n (fact (- n 1))))))")
        self.assertAlmostEqual(self.ev("(circle-area (fact 10))") / 4.1369087198e+13, 1.0)

    def test_first_and_rest_as_names_for_car_and_cdr(self):
        # Norvig defines them himself; Lispy already has both, and redefining works.
        self.ev_all("(define first car)", "(define rest cdr)")
        self.assertEqual(self.ev("(first (list 1 2 3))"), 1)
        self.assertEqual(self.ev("(rest (list 1 2 3))"), [2, 3])

    def test_count(self):
        # Norvig's count uses equal? (see KnownGapsTest); = does the same job in Lispy.
        # It also relies on (+ #t ...) counting #t as 1, as in Python.
        self.ev_all("(define first car)", "(define rest cdr)",
                    "(define count (lambda (item L) (if L (+ (= item (first L)) (count item (rest L))) 0)))")
        self.assertEqual(self.ev("(count 0 (list 0 1 2 3 0 0))"), 3)
        self.assertEqual(
            self.ev("(count (quote the) (quote (the more the merrier the bigger the better)))"), 4)

    def test_twice_and_repeat(self):
        self.ev_all("(define twice (lambda (x) (* 2 x)))",
                    "(define repeat (lambda (f) (lambda (x) (f (f x)))))")
        self.assertEqual(self.ev("(twice 5)"), 10)
        self.assertEqual(self.ev("((repeat twice) 10)"), 40)
        self.assertEqual(self.ev("((repeat (repeat twice)) 10)"), 160)
        self.assertEqual(self.ev("((repeat (repeat (repeat twice))) 10)"), 2560)
        self.assertEqual(self.ev("((repeat (repeat (repeat (repeat twice)))) 10)"), 655360)

    def test_pow(self):
        self.assertEqual(self.ev("(pow 2 16)"), 65536.0)

    def test_fib_and_range(self):
        self.ev_all("(define fib (lambda (n) (if (< n 2) 1 (+ (fib (- n 1)) (fib (- n 2))))))",
                    "(define range (lambda (a b) (if (= a b) (quote ()) (cons a (range (+ a 1) b)))))")
        self.assertEqual(self.show("(range 0 10)"), "(0 1 2 3 4 5 6 7 8 9)")
        self.assertEqual(self.show("(map fib (range 0 10))"), "(1 1 2 3 5 8 13 21 34 55)")
        self.assertEqual(
            self.show("(map fib (range 0 20))"),
            "(1 1 2 3 5 8 13 21 34 55 89 144 233 377 610 987 1597 2584 4181 6765)")

    def test_quote(self):
        self.assertEqual(self.ev("(quote (the more the merrier))"),
                         ['the', 'more', 'the', 'merrier'])
        self.assertEqual(self.ev("'(a b)"), ['a', 'b'])   # Lispy's ' shorthand

    def test_lambda_closes_over_its_environment(self):
        self.ev("(define adder (lambda (n) (lambda (x) (+ x n))))")
        self.ev("(define add3 (adder 3))")
        self.assertEqual(self.ev("(add3 4)"), 7)

    def test_procedure_parameters_shadow_globals(self):
        self.ev_all("(define x 1)", "(define f (lambda (x) (* x 10)))")
        self.assertEqual(self.ev("(f 5)"), 50)
        self.assertEqual(self.ev("x"), 1)

    def test_make_account_with_set(self):
        # Norvig's set! example: a bank account that remembers its balance.
        self.ev("""(define make-account
                     (lambda (balance)
                       (lambda (amt)
                         (begin (set! balance (+ balance amt))
                                balance))))""")
        self.ev("(define account1 (make-account 100.00))")
        self.assertEqual(self.ev("(account1 -20.00)"), 80.0)
        self.assertEqual(self.ev("(account1 -20.00)"), 60.0)
        self.ev("(define account2 (make-account 50))")
        self.assertEqual(self.ev("(account2 10)"), 60)
        self.assertEqual(self.ev("(account1 0)"), 60.0)   # each account has its own balance

    def test_set_of_undefined_variable_is_an_error(self):
        with self.assertRaises(NameError):
            self.ev("(set! nowhere 1)")


class StandardEnvTest(LispyTestCase):
    """The procedures in Norvig's standard_env() that Lispy also has."""

    def test_arithmetic_and_comparison(self):
        cases = {"(+ 2 3)": 5, "(- 2 3)": -1, "(* 2 3)": 6, "(/ 6 4)": 1.5,
                 "(> 2 3)": False, "(< 2 3)": True, "(>= 3 3)": True,
                 "(<= 4 3)": False, "(= 3 3)": True}
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(self.ev(source), expected)

    def test_math_module(self):
        self.assertAlmostEqual(self.ev("pi"), 3.141592653589793)
        self.assertAlmostEqual(self.ev("e"), 2.718281828459045)
        self.assertEqual(self.ev("(sqrt 16)"), 4.0)
        self.assertEqual(self.ev("(floor 2.7)"), 2)
        self.assertAlmostEqual(self.ev("(sin 0)"), 0.0)

    def test_numbers(self):
        self.assertEqual(self.ev("(abs -3)"), 3)
        self.assertEqual(self.ev("(max 1 5 3)"), 5)
        self.assertEqual(self.ev("(min 1 5 3)"), 1)
        self.assertEqual(self.ev("(round 2.6)"), 3)

    def test_lists(self):
        self.assertEqual(self.ev("(append (list 1 2) (list 3))"), [1, 2, 3])
        self.assertEqual(self.ev("(car (list 1 2 3))"), 1)
        self.assertEqual(self.ev("(cdr (list 1 2 3))"), [2, 3])
        self.assertEqual(self.ev("(cons 0 (list 1 2))"), [0, 1, 2])
        self.assertEqual(self.ev("(length (list 1 2 3))"), 3)
        self.assertEqual(self.ev("(list 1 2 3)"), [1, 2, 3])
        self.assertEqual(self.ev("(map abs (list -1 2 -3))"), [1, 2, 3])

    def test_car_of_empty_list(self):
        # Intentional difference: Norvig's car raises IndexError on ();
        # Lispy's car (and first) give () back.
        self.assertEqual(self.ev("(car (quote ()))"), [])

    def test_predicates(self):
        self.assertIs(self.ev("(null? (quote ()))"), True)
        self.assertIs(self.ev("(null? (list 1))"), False)
        self.assertIs(self.ev("(not #f)"), True)
        self.assertIs(self.ev("(not 1)"), False)
        self.assertIs(self.ev("(number? 3.5)"), True)
        self.assertIs(self.ev("(number? (quote a))"), False)
        self.assertIs(self.ev("(symbol? (quote a))"), True)
        self.assertIs(self.ev("(symbol? 3)"), False)

    def test_begin(self):
        # Norvig: begin is a procedure returning its last argument; Lispy: a special form.
        self.assertEqual(self.ev("(begin 1 2 3)"), 3)

    def test_procedures_are_first_class(self):
        self.assertEqual(self.ev("((if #t + -) 5 3)"), 8)
        self.assertEqual(self.ev("((if #f + -) 5 3)"), 2)


class NorvigLispyTestSuite(LispyTestCase):
    """lis_tests from Norvig's lispytest.py, run in order in one environment."""

    lis_tests = [
        ("(quote (testing 1 (2.0) -3.14e159))", ['testing', 1, [2.0], -3.14e159]),
        ("(+ 2 2)", 4),
        ("(+ (* 2 100) (* 1 10))", 210),
        ("(if (> 6 5) (+ 1 1) (+ 2 2))", 2),
        ("(if (< 6 5) (+ 1 1) (+ 2 2))", 4),
        ("(define x 3)", None),
        ("x", 3),
        ("(+ x x)", 6),
        ("(begin (define x 1) (set! x (+ x 1)) (+ x 1))", 3),
        ("((lambda (x) (+ x x)) 5)", 10),
        ("(define twice (lambda (x) (* 2 x)))", None),
        ("(twice 5)", 10),
        ("(define compose (lambda (f g) (lambda (x) (f (g x)))))", None),
        ("((compose list twice) 5)", [10]),
        ("(define repeat (lambda (f) (compose f f)))", None),
        ("((repeat twice) 5)", 20),
        ("((repeat (repeat twice)) 5)", 80),
        ("(define fact (lambda (n) (if (<= n 1) 1 (* n (fact (- n 1))))))", None),
        ("(fact 3)", 6),
        ("(fact 50)", 30414093201713378043612608166064768844377641568960512000000000000),
        ("(define abs (lambda (n) ((if (> n 0) + -) 0 n)))", None),
        ("(list (abs -3) (abs 0) (abs 3))", [3, 0, 3]),
        ("""(define combine (lambda (f)
             (lambda (x y)
               (if (null? x) (quote ())
                   (f (list (car x) (car y))
                      ((combine f) (cdr x) (cdr y)))))))""", None),
        ("(define zip (combine cons))", None),
        ("(zip (list 1 2 3 4) (list 5 6 7 8))", [[1, 5], [2, 6], [3, 7], [4, 8]]),
        ("""(define riff-shuffle (lambda (deck) (begin
             (define take (lambda (n seq) (if (<= n 0) (quote ()) (cons (car seq) (take (- n 1) (cdr seq))))))
             (define drop (lambda (n seq) (if (<= n 0) seq (drop (- n 1) (cdr seq)))))
             (define mid (lambda (seq) (/ (length seq) 2)))
             ((combine append) (take (mid deck) deck) (drop (mid deck) deck)))))""", None),
        ("(riff-shuffle (list 1 2 3 4 5 6 7 8))", [1, 5, 2, 6, 3, 7, 4, 8]),
        ("((repeat riff-shuffle) (list 1 2 3 4 5 6 7 8))", [1, 3, 5, 7, 2, 4, 6, 8]),
        ("(riff-shuffle (riff-shuffle (riff-shuffle (list 1 2 3 4 5 6 7 8))))",
         [1, 2, 3, 4, 5, 6, 7, 8]),
    ]

    def test_lis_tests(self):
        for source, expected in self.lis_tests:
            with self.subTest(source.split('\n')[0]):
                self.assertEqual(self.ev(source), expected)


class KnownGapsTest(LispyTestCase):
    """Procedures in Norvig's standard_env() that Lispy does not have yet (TODO.md).

    Each is an expected failure. When one is implemented, unittest reports an
    "unexpected success": remove its @expectedFailure so it becomes a normal test.
    """

    @unittest.expectedFailure
    def test_equal(self):
        self.assertIs(self.ev("(equal? (list 1 2) (list 1 2))"), True)

    @unittest.expectedFailure
    def test_count_with_equal(self):
        self.ev_all("(define first car)", "(define rest cdr)",
                    "(define count (lambda (item L) (if L (+ (equal? item (first L)) (count item (rest L))) 0)))")
        self.assertEqual(self.ev("(count 0 (list 0 1 2 3 0 0))"), 3)

    @unittest.expectedFailure
    def test_eq(self):
        self.ev("(define a (list 1))")
        self.assertIs(self.ev("(eq? a a)"), True)

    @unittest.expectedFailure
    def test_expt(self):
        self.assertEqual(self.show("(list (+ 1 1) (+ 2 2) (* 2 3) (expt 2 3))"), "(2 4 6 8)")

    @unittest.expectedFailure
    def test_apply(self):
        self.assertEqual(self.ev("(apply + (list 1 2))"), 3)

    @unittest.expectedFailure
    def test_list_predicate(self):
        self.assertIs(self.ev("(list? (list 1))"), True)

    @unittest.expectedFailure
    def test_procedure_predicate(self):
        self.assertIs(self.ev("(procedure? car)"), True)

    @unittest.expectedFailure
    def test_print(self):
        self.ev("(print 1)")

    @unittest.expectedFailure
    def test_map_over_two_lists(self):
        # Norvig's map is Python's map, so it takes several lists.
        self.assertEqual(self.ev("(map + (list 1 2) (list 10 20))"), [11, 22])


if __name__ == '__main__':
    unittest.main()
