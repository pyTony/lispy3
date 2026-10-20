"""Executable acceptance tests for mini-basic extensions.

Pending features deliberately remain ordinary failing tests: do not skip them
or mark them expected failures. Implement one behavior at a time and keep the
resulting green test as regression coverage.

Run: python -m pytest tests/test_mini_basic_tdd.py -q

Priority and progress are tracked in TODO.md. NestedJumpRegressionTest is now
green; SubroutineAcceptanceTest remains red for the upcoming improvements.
Numeric-label variants were run on BBCSDL 1.44a; see compare/reference/README.md.
The immediate-exit case does not establish compatible loop-stack cleanup.
"""
from test_mini_basic_reader import ReaderTestCase


class ExistingExtensionsTest(ReaderTestCase):
    """Green controls for features the upcoming changes must preserve."""

    def test_data_read_restore_rewinds(self):
        self.assertEqual(self.run_bbc(
            'DATA "first", 7\nREAD a$, n\nPRINT a$;n\n'
            'RESTORE\nREAD b$, m\nPRINT b$;m'), 'first7\nfirst7\n')

    def test_multidimensional_array_has_inclusive_bounds(self):
        self.assertEqual(self.run_bbc(
            'DIM a(2,3)\na(2,3)=9\nPRINT ;a(2,3);",";a(0,0)'),
            '9,0\n')

    def test_top_level_goto_skips_statement(self):
        self.assertEqual(self.run_bbc(
            '10 GOTO 30\n20 PRINT "wrong"\n30 PRINT "landed"'),
            'landed\n')


class NestedJumpRegressionTest(ReaderTestCase):
    """Targets within an active structured body must retain its continuation."""

    def test_goto_within_for_preserves_next(self):
        self.assertEqual(self.run_bbc(
            '10 FOR i=1 TO 3\n20 GOTO 40\n30 PRINT "wrong"\n'
            '40 PRINT ;i\n50 NEXT\n60 PRINT "done"'),
            '1\n2\n3\ndone\n')

    def test_goto_within_while_preserves_condition(self):
        self.assertEqual(self.run_bbc(
            '10 n=0\n20 WHILE n<2\n30 n+=1\n40 GOTO 60\n'
            '50 PRINT "wrong"\n60 PRINT ;n\n70 ENDWHILE\n80 PRINT "done"'),
            '1\n2\ndone\n')

    def test_goto_within_if_preserves_following_statement(self):
        self.assertEqual(self.run_bbc(
            '10 IF TRUE THEN\n20 GOTO 40\n30 PRINT "wrong"\n'
            '40 PRINT "inside"\n50 ENDIF\n60 PRINT "after"'),
            'inside\nafter\n')

    def test_jump_from_inner_body_reaches_active_outer_body(self):
        self.assertEqual(self.run_bbc(
            '10 FOR i=1 TO 2\n20 IF TRUE THEN\n30 GOTO 60\n'
            '40 ENDIF\n50 PRINT "wrong"\n60 PRINT ;i\n70 NEXT\n'
            '80 PRINT "done"'), '1\n2\ndone\n')

    def test_jump_out_of_nested_body_reaches_program_label(self):
        # BBCSDL case 5 prints "out" and terminates too. Continuing after an
        # abandoned loop can expose stack differences; this does not test that.
        self.assertEqual(self.run_bbc(
            '10 FOR i=1 TO 2\n20 IF TRUE THEN\n30 GOTO 80\n'
            '40 ENDIF\n50 PRINT "wrong"\n60 NEXT\n'
            '80 PRINT "out"'), 'out\n')

    def test_backward_jump_within_while_body(self):
        self.assertEqual(self.run_bbc(
            '10 n=0\n20 WHILE n<3\n30 n+=1\n'
            '40 IF n<3 THEN GOTO 30\n50 PRINT ;n\n60 ENDWHILE'), '3\n')

    def test_jump_within_else_branch(self):
        self.assertEqual(self.run_bbc(
            '10 IF FALSE THEN\n20 PRINT "wrong"\n30 ELSE\n'
            '40 GOTO 60\n50 PRINT "wrong"\n60 PRINT "else"\n'
            '70 ENDIF\n80 PRINT "after"'), 'else\nafter\n')

    def test_on_goto_within_repeat_preserves_until(self):
        self.assertEqual(self.run_bbc(
            '10 n=0\n20 REPEAT\n30 n+=1\n40 ON 1 GOTO 60,50\n'
            '50 PRINT "wrong"\n60 PRINT ;n\n70 UNTIL n=2'), '1\n2\n')

    def test_jump_within_case_branch(self):
        self.assertEqual(self.run_bbc(
            'CASE 1 OF\nWHEN 1\nGOTO hit\n'
            'PRINT "wrong"\n(hit) PRINT "case"\nOTHERWISE\n'
            'PRINT "wrong"\nENDCASE\nPRINT "after"'),
            'case\nafter\n')

    def test_missing_label_still_reports_target(self):
        with self.assertRaisesRegex(Exception, 'GOTO: unknown label 999'):
            self.run_bbc('10 WHILE TRUE\n20 GOTO 999\n30 ENDWHILE')


class NumberedCaseRegressionTest(ReaderTestCase):
    """Numbered clause headers, including the confirmed BBCSDL case 9."""

    def test_bbcsdl_case_9_with_numbered_clause_headers(self):
        self.assertEqual(self.run_bbc(
            '9010 CASE 1 OF\n9020 WHEN 1\n9030 GOTO 9050\n'
            '9040 PRINT "wrong"\n9050 PRINT "case"\n9060 OTHERWISE\n'
            '9070 PRINT "wrong"\n9080 ENDCASE\n9090 PRINT "after"'),
            'case\nafter\n')

    def test_numbered_nested_cases_and_multiple_when_values(self):
        self.assertEqual(self.run_bbc(
            '10 FOR n=1 TO 4\n20 CASE n OF\n30 WHEN 1\n'
            '40 PRINT "one"\n50 WHEN 2,3\n60 CASE n OF\n'
            '70 WHEN 2\n80 PRINT "two"\n90 OTHERWISE\n'
            '100 PRINT "three"\n110 ENDCASE\n120 OTHERWISE\n'
            '130 PRINT "four"\n140 ENDCASE\n150 NEXT\n160 PRINT "done"'),
            'one\ntwo\nthree\nfour\ndone\n')

    def test_clause_line_labels_are_available_to_restore(self):
        source = (
            '10 CASE 1 OF\n20 WHEN 1\n30 DATA "first"\n'
            '40 WHEN 2\n50 DATA "second"\n60 OTHERWISE\n'
            '70 DATA "fallback"\n80 ENDCASE\n'
            '90 RESTORE 20\n100 READ a$\n110 PRINT a$\n'
            '120 RESTORE 40\n130 READ b$\n140 PRINT b$\n'
            '150 RESTORE 60\n160 READ c$\n170 PRINT c$')
        self.assertEqual(self.run_bbc(source), 'first\nsecond\nfallback\n')
        # ENDCASE is still a source label, after all three DATA items.
        self.assertEqual(self.ev('(get bbc-data-labels 80)'), 3)


class SubroutineAcceptanceTest(ReaderTestCase):
    """Next feature: return to the exact statement following each GOSUB."""

    def test_gosub_returns_to_same_line(self):
        self.assertEqual(self.run_bbc(
            '10 GOSUB 100 : PRINT "back"\n20 END\n'
            '100 PRINT "sub" : RETURN'), 'sub\nback\n')

    def test_nested_gosub_returns_in_stack_order(self):
        self.assertEqual(self.run_bbc(
            '10 GOSUB 100 : PRINT "main" : END\n'
            '100 PRINT "outer" : GOSUB 200 : PRINT "outer back" : RETURN\n'
            '200 PRINT "inner" : RETURN'),
            'outer\ninner\nouter back\nmain\n')

    def test_gosub_in_for_preserves_loop(self):
        self.assertEqual(self.run_bbc(
            '10 FOR i=1 TO 2\n20 GOSUB 100\n30 NEXT\n'
            '40 PRINT "done" : END\n100 PRINT ;i : RETURN'),
            '1\n2\ndone\n')

    def test_on_gosub_selects_one_based_target_and_returns(self):
        self.assertEqual(self.run_bbc(
            '10 ON 2 GOSUB 100,200 : PRINT "back" : END\n'
            '100 PRINT "wrong" : RETURN\n200 PRINT "second" : RETURN'),
            'second\nback\n')
