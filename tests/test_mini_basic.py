"""lisp/mini-basic.lisp: structured BBC BASIC statements as lispy3 macros."""
import contextlib
import io
import unittest

from support import LispyTestCase, lispy3


class MiniBasicTestCase(LispyTestCase):

    def setUp(self):
        super().setUp()
        lispy3.load_workspace('mini-basic')

    def run_basic(self, *stmts: str) -> str:
        """Run the statements as one (bbc-program ...) and return what it printed."""
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.ev('(bbc-program ' + ' '.join(stmts) + ')')
        return out.getvalue()

    def expansion(self, source: str) -> str:
        return lispy3.lisp_str(lispy3.parse(source))


class PrintTest(MiniBasicTestCase):

    def test_numbers_are_right_justified_until_a_semicolon(self):
        self.assertEqual(self.run_basic('(PRINT 1 :semi 2 :comma 3)'),
                         '         12                  3\n')

    def test_strings_are_not_justified(self):
        self.assertEqual(self.run_basic('(PRINT "A" :semi 1 :semi "B")'), 'A1B\n')

    def test_comma_moves_to_the_next_zone(self):
        self.assertEqual(self.run_basic('(PRINT "AB" :comma "C")'), 'AB        C\n')

    def test_trailing_separator_keeps_the_line(self):
        self.assertEqual(self.run_basic('(PRINT "A" :semi)', '(PRINT "B")'), 'AB\n')

    def test_apostrophe_starts_a_new_line(self):
        self.assertEqual(self.run_basic('(PRINT "A" :nl "B")'), 'A\nB\n')

    def test_tab_and_spc(self):
        self.assertEqual(self.run_basic('(PRINT (TAB 3) "x" :semi (SPC 2) "y")'), '   x  y\n')
        self.assertEqual(self.run_basic('(PRINT "abcdef" :semi (TAB 2) "x")'), 'abcdef\n  x\n')

    def test_number_format(self):
        self.assertEqual(self.run_basic('(PRINT (/ 1 3) :semi " " :semi 2.0 :semi " " :semi 1e10'
                                        ' :semi " " :semi 1.5e-5 :semi " " :semi (> 2 1))'),
                         '0.333333333 2 1E10 1.5E-5 -1\n')

    def test_empty_print(self):
        self.assertEqual(self.run_basic('(PRINT)'), '\n')


class AssignmentTest(MiniBasicTestCase):

    def test_variables_start_at_zero_and_empty(self):
        self.assertEqual(self.run_basic('(PRINT :semi a :semi "[" :semi b$ :semi "]")', '(LET a 1)', '(LET b$ "x")'),
                         '0[]\n')

    def test_integer_variables_drop_the_fraction(self):
        self.assertEqual(self.run_basic('(LET a% 3.7)', '(LET b% -3.7)', '(PRINT :semi a% :semi " " :semi b%)'),
                         '3 -3\n')

    def test_variable_names_used_by_the_runtime(self):
        # (format t ...) would print nothing if a program's own t were used
        self.assertEqual(self.run_basic('(LET t 5)', '(PRINT t)'), '         5\n')

    def test_true_and_false(self):
        self.assertEqual(self.run_basic('(PRINT :semi TRUE :semi " " :semi FALSE)'), '-1 0\n')


class ControlTest(MiniBasicTestCase):

    def test_if_else(self):
        self.assertEqual(self.run_basic('(LET x 3)',
                                        '(IF (> x 2) (PRINT "big") ELSE (PRINT "small"))',
                                        '(IF (< x 2) (PRINT "never"))'),
                         'big\n')

    def test_if_uses_bbc_truth(self):
        self.assertEqual(self.run_basic('(IF 0 (PRINT "zero") ELSE (PRINT "false"))',
                                        '(IF TRUE (PRINT "true"))'),
                         'false\ntrue\n')

    def test_for_next(self):
        self.assertEqual(self.run_basic('(FOR i 1 3 (PRINT :semi i :semi " " :semi))', '(PRINT "/" :semi i)'),
                         '1 2 3 /4\n')

    def test_for_step(self):
        self.assertEqual(self.run_basic('(FOR i 10 1 STEP -4 (PRINT :semi i :semi " " :semi))', '(PRINT)'),
                         '10 6 2 \n')
        self.assertEqual(self.run_basic('(LET s 2)', '(FOR i 1 5 STEP s (PRINT :semi i :semi))', '(PRINT)'),
                         '135\n')

    def test_for_runs_at_least_once(self):
        self.assertEqual(self.run_basic('(FOR i 5 1 (PRINT "once"))'), 'once\n')

    def test_repeat_until(self):
        self.assertEqual(self.run_basic('(LET k 0)', '(REPEAT (LET k (+ k 1)) UNTIL (>= k 4))', '(PRINT :semi k :semi)'),
                         '4')

    def test_while(self):
        self.assertEqual(self.run_basic('(LET k 10)', '(WHILE (< k 3) (LET k (+ k 1)))', '(PRINT :semi k :semi)'),
                         '10')
        self.assertEqual(self.run_basic('(LET k 0)', '(WHILE (< k 3) (LET k (+ k 1)))', '(PRINT :semi k :semi)'),
                         '3')

    def test_case(self):
        program = ('(FOR n 1 4 (CASE n (WHEN (1 2) (PRINT "low" :semi)) (WHEN (3) (PRINT "three" :semi))'
                   ' (OTHERWISE (PRINT "other" :semi))) (PRINT " " :semi))')
        self.assertEqual(self.run_basic(program), 'low low three other ')

    def test_case_strings(self):
        self.assertEqual(self.run_basic('(LET a$ "yes")',
                                        '(CASE a$ (WHEN ("no") (PRINT "N")) (WHEN ("yes" "y") (PRINT "Y")))'),
                         'Y\n')

    def test_exits(self):
        self.assertEqual(self.run_basic('(FOR i 1 10 (IF (= i 3) (EXIT-FOR)))', '(PRINT :semi i :semi)'), '3')
        self.assertEqual(self.run_basic('(LET k 0)', '(REPEAT (LET k (+ k 1)) (IF (= k 2) (EXIT-REPEAT)) UNTIL FALSE)',
                                        '(PRINT :semi k :semi)'), '2')
        self.assertEqual(self.run_basic('(LET k 0)', '(WHILE TRUE (LET k (+ k 1)) (IF (= k 5) (EXIT-WHILE)))',
                                        '(PRINT :semi k :semi)'), '5')

    def test_exit_for_leaves_only_the_inner_loop(self):
        self.assertEqual(self.run_basic('(FOR i 1 2 (FOR j 1 9 (IF (> j i) (EXIT-FOR)) (PRINT :semi j :semi)))', '(PRINT)'),
                         '112\n')

    def test_end(self):
        self.assertEqual(self.run_basic('(PRINT "a")', '(END)', '(PRINT "b")'), 'a\n')

    def test_end_inside_a_procedure(self):
        self.assertEqual(self.run_basic('(PROC stop)', '(PRINT "b")', '(DEF-PROC (stop) (PRINT "a") (END))'), 'a\n')

    def test_errors_still_stop_the_program(self):
        with self.assertRaises(Exception):
            self.run_basic('(FOR i 1 3 (IF (= i 2) (EXIT-FOR)) (PRINT undefined-variable))')


class ProcedureTest(MiniBasicTestCase):

    def test_procedure_with_parameters(self):
        self.assertEqual(self.run_basic('(PROC greet "Tony" 2)',
                                        '(DEF-PROC (greet name$ times) (FOR i 1 times (PRINT "Hi " :semi name$)))'),
                         'Hi Tony\nHi Tony\n')

    def test_recursive_function(self):
        program = ('(DEF-FN (fact n) (IF (< n 2) (FN= 1) ELSE (FN= (* n (FN fact (- n 1))))))',
                   '(PRINT :semi (FN fact 10) :semi)')
        self.assertEqual(self.run_basic(*program), '3628800')

    def test_tail_results_need_no_exception(self):
        code = self.expansion('(DEF-FN (fact n) (IF (< n 2) (FN= 1) ELSE (FN= (* n (FN fact (- n 1))))))')
        # Cleanup still needs a handler; tail results must not use a return signal.
        self.assertNotIn('bbc:return', code)
        code = self.expansion('(DEF-FN (f x) (IF (< x 0) (FN= 0)) (FN= x))')
        self.assertIn('bbc:return', code)

    def test_early_return(self):
        program = ('(DEF-FN (sign x) (IF (< x 0) (FN= -1)) (IF (= x 0) (FN= 0)) (FN= 1))',
                   '(PRINT (FN sign -5) :semi (FN sign 0) :semi (FN sign 7))')
        self.assertEqual(self.run_basic(*program), '        -101\n')

    def test_endproc_leaves_early(self):
        program = ('(PROC p 1)', '(PROC p -1)',
                   '(DEF-PROC (p x) (IF (< x 0) (ENDPROC)) (PRINT "positive"))')
        self.assertEqual(self.run_basic(*program), 'positive\n')

    def test_early_return_from_inside_a_loop(self):
        program = ('(DEF-FN (first-over limit) (FOR i 1 100 (IF (> (* i i) limit) (FN= i))) (FN= -1))',
                   '(PRINT :semi (FN first-over 50) :semi)')
        self.assertEqual(self.run_basic(*program), '8')

    def test_parameters_and_locals_are_restored(self):
        program = ('(LET x 1)', '(LET y 2)', '(PROC p 10)', '(PRINT :semi x :semi " " :semi y :semi)',
                   '(DEF-PROC (p x) (LOCAL y) (LET y (* x 2)) (PRINT :semi x :semi " " :semi y))')
        self.assertEqual(self.run_basic(*program), '10 20\n1 2')

    def test_scope_is_dynamic(self):
        # As in BBC BASIC, a procedure sees its caller's LOCAL variables
        program = ('(LET v "global")', '(PROC outer)', '(PROC show)',
                   '(DEF-PROC (outer) (LOCAL v) (LET v "outer") (PROC show))',
                   '(DEF-PROC (show) (PRINT v))')
        self.assertEqual(self.run_basic(*program), 'outer\nglobal\n')

    def test_definitions_may_follow_the_main_part(self):
        self.assertEqual(self.run_basic('(PRINT :semi (FN twice 21) :semi)', '(END)', '(DEF-FN (twice n) (FN= (* 2 n)))'),
                         '42')


if __name__ == '__main__':
    unittest.main()
