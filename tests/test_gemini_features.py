"""Tests for the features the Gemini Argon version added to Lispy.

Most of them were the open items in TODO.md: variadic arithmetic, cond,
and/or, macros and quasiquote, tail calls, try/error, and the list, string
and map built-ins. Run from the repository folder:

    python -m unittest discover tests
"""
import contextlib
import io
import os
import tempfile
import time
import unittest

from support import LispyTestCase, lispy3


class NumbersTest(LispyTestCase):

    def test_variadic_arithmetic(self):
        self.assertEqual(self.ev("(+ 1 2 3 4)"), 10)
        self.assertEqual(self.ev("(- 10 1 2)"), 7)
        self.assertEqual(self.ev("(- 5)"), -5)
        self.assertEqual(self.ev("(* 2 3 4)"), 24)
        self.assertEqual(self.ev("(/ 12 2 3)"), 2.0)

    def test_variadic_comparison(self):
        self.assertIs(self.ev("(< 1 2 3)"), True)
        self.assertIs(self.ev("(< 1 3 2)"), False)
        self.assertIs(self.ev("(= 2 2 2)"), True)
        self.assertIs(self.ev("(>= 3 3 1)"), True)

    def test_quotient_and_modulo(self):
        self.assertEqual(self.ev("(quotient 17 5)"), 3)
        self.assertEqual(self.ev("(quotient -17 5)"), -3)
        self.assertEqual(self.ev("(modulo 17 5)"), 2)
        self.assertEqual(self.ev("(modulo -7 3)"), 2)

    def test_quotient_is_exact_for_big_numbers(self):
        self.assertEqual(self.ev("(quotient (expt 10 30) 7)"), 10 ** 30 // 7)

    def test_expt(self):
        self.assertEqual(self.ev("(expt 2 100)"), 2 ** 100)


class ControlTest(LispyTestCase):

    def test_cond(self):
        self.assertEqual(self.ev("(cond ((> 1 2) 'a) ((< 1 2) 'b) (else 'c))"), 'b')
        self.assertEqual(self.ev("(cond ((> 1 2) 'a) (else 'c))"), 'c')
        self.assertIsNone(self.ev("(cond (#f 1))"))

    def test_and_or_short_circuit(self):
        self.assertEqual(self.ev("(and 1 2 3)"), 3)
        self.assertIs(self.ev("(and 1 #f (car))"), False)   # (car) is never run
        self.assertEqual(self.ev("(or #f 0 7)"), 7)
        self.assertIs(self.ev("(or #f #f)"), False)
        self.assertEqual(self.ev("(or 5 (car))"), 5)

    def test_and_treats_zero_and_empty_list_as_false(self):
        self.assertEqual(self.ev("(and 1 0 3)"), 0)
        self.assertEqual(self.ev("(and 1 '() 3)"), [])

    def test_if_without_else(self):
        self.assertIsNone(self.ev("(if #f 1)"))

    def test_dotimes(self):
        self.ev("(define total 0)")
        self.ev("(dotimes [i 5] (set! total (+ total i)))")
        self.assertEqual(self.ev("total"), 10)
        self.assertEqual(self.ev("(dotimes [i 4 i] 0)"), 3)

    def test_for_each(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertIsNone(self.ev("(for-each display '(1 2))"))
        self.assertEqual(out.getvalue(), "1\n2\n")

    def test_try_catches_lisp_and_python_errors(self):
        self.assertEqual(self.ev('(try (error "boom" 42) (catch e (str "caught: " e)))').value,
                         "caught: boom 42")
        self.assertEqual(self.ev("(try (/ 1 0) (catch e e))").value, "division by zero")
        self.assertEqual(self.ev("(try (undefined-thing) 'fallback)"), 'fallback')

    def test_error_without_try_raises(self):
        with self.assertRaises(lispy3.LispyError):
            self.ev('(error "bad")')


class FunctionsTest(LispyTestCase):

    def test_define_shorthand_with_several_body_expressions(self):
        self.ev("(define (two x) (define y (* x 2)) (+ y 1))")
        self.assertEqual(self.ev("(two 5)"), 11)

    def test_lambda_and_let_with_several_body_expressions(self):
        self.assertEqual(self.ev("((lambda [x] (define y 1) (+ x y)) 1)"), 2)
        self.assertEqual(self.ev("(let [a 1 b (+ a 1)] (define c 3) (+ a b c))"), 6)

    def test_rest_parameters(self):
        self.ev("(define (f a & more) more)")
        self.assertEqual(self.ev("(f 1 2 3)"), [2, 3])
        self.ev("(define (g a . more) more)")
        self.assertEqual(self.ev("(g 1 2 3)"), [2, 3])
        self.ev("(define h (lambda args args))")
        self.assertEqual(self.ev("(h 1 2)"), [1, 2])

    def test_tail_calls_use_no_stack(self):
        self.ev("(define (count-down n) (if (= n 0) 'done (count-down (- n 1))))")
        self.assertEqual(self.ev("(count-down 100000)"), 'done')
        self.ev("(define (loop n acc) (cond ((= n 0) acc) (else (loop (- n 1) (+ acc 1)))))")
        self.assertEqual(self.ev("(loop 50000 0)"), 50000)

    def test_apply(self):
        self.assertEqual(self.ev("(apply + 1 2 '(3 4))"), 10)
        self.ev("(define (sum3 a b c) (+ a b c))")
        self.assertEqual(self.ev("(apply sum3 '(1 2 3))"), 6)


class MacroTest(LispyTestCase):

    def test_quasiquote(self):
        self.ev("(define xs '(2 3))")
        self.assertEqual(self.show("`(1 ,(+ 1 1) ,@xs 4)"), "(1 2 2 3 4)")
        self.assertEqual(self.show("`[a ,(+ 1 2)]"), "(a 3)")

    def test_define_macro(self):
        self.ev("(define-macro (unless c body) `(if ,c #f ,body))")
        self.assertEqual(self.ev("(unless #f 5)"), 5)
        self.assertIs(self.ev("(unless #t (car))"), False)

    def test_gensym_gives_new_symbols(self):
        self.assertNotEqual(self.ev("(gensym)"), self.ev("(gensym)"))


class ListTest(LispyTestCase):

    def test_list_built_ins(self):
        cases = {
            "(reverse '(1 2 3))": "(3 2 1)",
            "(nth '(a b c) 1)": "b",
            "(last '(1 2 3))": "3",
            "(range 5)": "(0 1 2 3 4)",
            "(range 1 10 3)": "(1 4 7)",
            "(reduce + '(1 2 3 4))": "10",
            "(reduce + 10 '(1 2 3))": "16",
            "(fold + 0 '(1 2 3))": "6",
            "(sort '(3 1 2))": "(1 2 3)",
            "(sort '(3 1 2) >)": "(3 2 1)",
            "(member 2 '(1 2 3))": "(2 3)",
            "(member 9 '(1 2 3))": "#f",
            "(append '(1 2) '(3) '(4 5))": "(1 2 3 4 5)",
            "(map + '(1 2) '(10 20))": "(11 22)",
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(self.show(source), expected)

    def test_predicates(self):
        cases = {
            "(list? '(1))": True, "(list? 5)": False,
            "(procedure? car)": True, "(procedure? 5)": False,
            "(eq? 'a 'a)": True, "(equal? '(1 (2)) '(1 (2)))": True,
            "(boolean? #f)": True, "(boolean? 0)": False,
            "(char? #\\a)": True, "(map? {:a 1})": True,
            "(empty? \"\")": True, "(empty? \"a\")": False, "(empty? {})": True,
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertIs(self.ev(source), expected)


class StringTest(LispyTestCase):

    def test_string_built_ins(self):
        cases = {
            '(substring "hello" 1 3)': '"el"',
            '(substring "hello" 2)': '"llo"',
            '(string-ref "hello" 1)': '#\\e',
            '(upcase "abc")': '"ABC"',
            '(downcase "ABC")': '"abc"',
            '(split "a b c")': '("a" "b" "c")',
            '(split "a,b" ",")': '("a" "b")',
            '(list->string (list #\\a #\\b))': '"ab"',
            '(string->list "ab")': '(#\\a #\\b)',
            '(string->number "42")': '42',
            '(string->number "4.5")': '4.5',
            '(string->number "x")': '#f',
            '(number->string 42)': '"42"',
            '(reverse "abc")': '"cba"',
            '(nth "abc" 2)': '#\\c',
            '(str "a" 1 \'b)': '"a1b"',
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(self.show(source), expected)

    def test_str_returns_a_real_string(self):
        self.assertIs(self.ev('(= (str 12) "12")'), True)

    def test_format(self):
        self.assertEqual(self.ev('(format "~a is ~s~%" "x" "y")').value, 'x is "y"\n')
        self.assertEqual(self.ev('(format "{} and {}" 1 2)').value, "1 and 2")

    def test_escapes_and_character_names(self):
        self.assertEqual(self.ev('"\\x41;\\u00e4"').value, "Aä")
        self.assertEqual(self.ev("#\\return").value, "\r")
        self.assertEqual(self.ev("#\\nul").value, "\0")
        self.assertEqual(self.ev("#\\x41").value, "A")

    def test_python_method_calls(self):
        self.ev('(define s "abc")')
        self.assertEqual(self.ev("(s/upper)").value, "ABC")
        self.assertEqual(self.ev('(s/replace "b" "X")').value, "aXc")
        self.assertEqual(self.ev('(str/join ", " \'("a" "b"))').value, "a, b")


class MapTest(LispyTestCase):

    def test_map_built_ins(self):
        cases = {
            "(assoc {:a 1} :b 2)": "{:a 1 :b 2}",
            "(dissoc {:a 1 :b 2} :a)": "{:b 2}",
            "(keys {:a 1 :b 2})": "(:a :b)",
            "(vals {:a 1 :b 2})": "(1 2)",
            "(contains? {:a 1} :a)": "#t",
            "(get {:a 1} :z 0)": "0",
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(self.show(source), expected)

    def test_assoc_leaves_the_original_alone(self):
        self.ev("(define m {:a 1})")
        self.ev("(assoc m :b 2)")
        self.assertEqual(self.show("m"), "{:a 1}")


class OutputTest(LispyTestCase):

    def output(self, source: str) -> str:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev(source)
        return out.getvalue()

    def test_print_puts_spaces_between_values(self):
        self.assertEqual(self.output("(print 1 \"two\" 'three)"), "1 two three\n")

    def test_newline(self):
        self.assertEqual(self.output("(newline)"), "\n")


class RestoredFeaturesTest(LispyTestCase):
    """Things the older Lispy had that the Gemini rewrite dropped, now back."""

    def output(self, source: str) -> str:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev(source)
        return out.getvalue()

    def test_vectors_and_clock(self):
        self.ev("(define v (make-vector 3 1))")
        self.ev("(vector-set! v 0 9)")
        self.assertEqual(self.ev("(vector-ref v 0)"), 9)
        self.assertEqual(self.show("v"), "(9 1 1)")
        self.ev("(define t0 (clock))")
        self.assertIs(self.ev("(>= (clock) t0)"), True)

    def test_clock_to_string_shows_local_date_and_time(self):
        text = self.ev("(clock->string)").value
        self.assertRegex(text, r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
        self.ev("(define t0 (clock))")
        self.assertEqual(self.ev('(clock->string t0 "%Y")').value, time.strftime("%Y"))
        self.assertEqual(self.ev('(clock->string "%Y")').value, time.strftime("%Y"))
        # an hour earlier on (clock) is an hour earlier on the wall clock
        hour_ago = time.strftime("%H", time.localtime(time.time() - 3600))
        self.assertEqual(self.ev('(clock->string (- t0 3600) "%H")').value, hour_ago)

    def test_common_lisp_time_functions(self):
        # CLtL2 25.4.1: universal time counts seconds from 1900-01-01 GMT
        self.assertEqual(self.ev("(encode-universal-time 0 0 0 1 1 1900 0)"), 0)
        self.assertEqual(self.ev("(decode-universal-time 0 0)"), [0, 0, 0, 1, 1, 1900, 0, False, 0])
        # zone is hours west of Greenwich, so New York (5) is behind GMT
        self.assertEqual(self.ev("(encode-universal-time 0 0 7 17 10 2026 5)"),
                         self.ev("(encode-universal-time 0 0 12 17 10 2026 0)"))
        self.ev("(define now (get-universal-time))")
        self.assertLessEqual(abs(self.ev("now") - (int(time.time()) + 2208988800)), 1)
        parts = self.ev("(decode-universal-time now)")
        self.assertEqual(self.ev("(encode-universal-time %s)" % " ".join(map(str, parts[:6]))), self.ev("now"))
        decoded = self.ev("(get-decoded-time)")
        self.assertEqual(len(decoded), 9)
        self.assertEqual(decoded[5], time.localtime().tm_year)
        self.assertEqual(self.ev("internal-time-units-per-second"), 1000)
        self.ev("(define t0 (get-internal-real-time))")
        self.ev("(sleep 0.02)")
        self.assertGreaterEqual(self.ev("(- (get-internal-real-time) t0)"), 15)
        self.assertGreaterEqual(self.ev("(get-internal-run-time)"), 0)

    def test_display_takes_several_values_and_ends_the_line(self):
        self.assertEqual(self.output('(display "a" 1 "b")'), "a1b\n")

    def test_append_joins_strings(self):
        self.assertEqual(self.ev('(append "ab" "cd")').value, "abcd")

    def test_help(self):
        self.assertIn("Special forms", self.output("(help)"))
        self.assertIn("quotient", self.output("(help 'quotient)"))
        self.assertIn("whole-number", self.output("(help quotient)"))
        self.assertIn("math", self.output("(help 'sqrt)"))

    def test_read_and_symbol_conversion(self):
        self.assertEqual(self.ev('(eval (read "(+ 1 2)"))'), 3)
        self.assertEqual(self.ev('(string->symbol "car")'), 'car')
        self.assertEqual(self.ev("(symbol->string 'car)").value, "car")

    def test_raw_strings_and_boolean_literals(self):
        self.assertEqual(self.ev('"""say "hi"\\n"""').value, 'say "hi"\\n')
        self.assertIs(self.ev("'#t"), True)

    def test_multi_line_string_keeps_the_repl_reading(self):
        self.assertEqual(lispy3.count_balance('(display "first line'), 1)

    def test_calling_a_string_explains_itself(self):
        with self.assertRaisesRegex(TypeError, "string->symbol"):
            self.ev('("abc" 1)')

    def test_pop_pose_without_a_pose_is_an_error(self):
        with self.assertRaises(IndexError):
            self.ev("(pop-pose)")

    def test_save_quotes_lists_and_symbols(self):
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, "ws")
            self.ev_all("(define v '(1 2))", "(define k 'car)", "(define (sq x) (* x x))")
            self.ev(f'(save "{name}")')
            lispy3.global_env.clear()
            lispy3.global_env.update(lispy3.standard_env())
            self.ev(f'(load "{name}")')
        self.assertEqual(self.show("v"), "(1 2)")
        self.assertEqual(self.ev("k"), 'car')
        self.assertEqual(self.ev("(sq 4)"), 16)

    def test_run_file(self):
        with tempfile.TemporaryDirectory() as folder:
            good = os.path.join(folder, "good.lisp")
            bad = os.path.join(folder, "bad.lisp")
            with open(good, "w", encoding="utf-8") as f:
                f.write('(display "hello")')
            with open(bad, "w", encoding="utf-8") as f:
                f.write("(car)")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertTrue(lispy3.run_file(good))
            self.assertEqual(out.getvalue(), "hello\n")
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertFalse(lispy3.run_file(bad))
            self.assertIn("Error", err.getvalue())


if __name__ == '__main__':
    unittest.main()
