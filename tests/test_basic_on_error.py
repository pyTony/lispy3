"""BBC BASIC error handling: ON ERROR, ERR, ERL, REPORT (lisp/mini-basic-error.lisp)."""
from test_mini_basic_reader import ReaderTestCase


class OnErrorTest(ReaderTestCase):

    def test_reference_handler_reports_err_erl_and_message(self):
        # The handler line of basic/reference/bbcsdl-jumps.bas
        self.assertEqual(self.run_bbc(
            '10 REM checks\n'
            '20 ON ERROR PRINT "ERROR ";ERR;" AT LINE ";ERL:REPORT:PRINT:END\n'
            '30 PRINT "start"\n40 PRINT 1/0\n50 PRINT "wrong"'),
            'start\nERROR 18 AT LINE 40\nDivision by zero\n')

    def test_missing_goto_target_matches_bbcsdl(self):
        # bbcsdl-jumps.bas case 10: BBCSDL 1.44a gives ERR 41 at line 10020
        self.assertEqual(self.run_bbc(
            '20 ON ERROR PRINT ;ERR;" ";ERL;" ";REPORT$:END\n'
            '10010 WHILE TRUE\n10020 GOTO 999\n10030 ENDWHILE'),
            '41 10020 No such line\n')

    def test_on_error_goto(self):
        self.assertEqual(self.run_bbc(
            '10 ON ERROR GOTO 100\n20 DIM a(3)\n30 a(7)=1\n40 PRINT "wrong"\n50 END\n'
            '100 PRINT REPORT$;" ";ERR;" at ";ERL'),
            'Subscript out of range 15 at 30\n')

    def test_handler_continues_into_the_following_lines(self):
        self.assertEqual(self.run_bbc(
            'n%=0\nON ERROR n%+=1:PRINT "again ";n%:IF n%=3 THEN END\nPRINT 1/0'),
            'again 1\nagain 2\nagain 3\n')

    def test_handler_is_skipped_when_set(self):
        self.assertEqual(self.run_bbc('ON ERROR PRINT "wrong"\nPRINT "ok"'), 'ok\n')

    def test_error_inside_proc_reports_proc_line(self):
        self.assertEqual(self.run_bbc(
            '10 ON ERROR GOTO 100\n20 PROCx\n30 END\n100 PRINT REPORT$;" at ";ERL:END\n'
            '200 DEF PROCx\n210 LOCAL i\n220 i=1/0\n230 ENDPROC'),
            'Division by zero at 220\n')

    def test_handler_set_in_finished_proc_still_traps(self):
        self.assertEqual(self.run_bbc(
            '10 PROCsetup\n20 PRINT FNbad(2)\n30 PRINT "wrong"\n40 END\n'
            '100 DEF PROCsetup\n110 ON ERROR PRINT "late ";REPORT$;" ";ERL:END\n120 ENDPROC\n'
            '200 DEF FNbad(x)=x DIV 0'),
            'late Division by zero 200\n')

    def test_on_error_local_and_error_statement(self):
        self.assertEqual(self.run_bbc(
            'FOR i%=1 TO 3 : PROCtry(i%) : NEXT\nPRINT "done"\n'
            'DEF PROCtry(n%)\nON ERROR LOCAL PRINT "caught ";n%;" ";ERR;" ";REPORT$:ENDPROC\n'
            'IF n%=2 THEN ERROR 100,"Two is bad"\nPRINT "ok ";n%\nENDPROC'),
            'ok 1\ncaught 2 100 Two is bad\nok 3\ndone\n')

    def test_on_error_local_is_restored_when_proc_returns(self):
        with self.assertRaisesRegex(Exception, 'division by zero'):
            self.run_bbc('PROClocal\nPRINT 1/0\nDEF PROClocal\nON ERROR LOCAL PRINT "wrong"\nENDPROC')

    def test_on_error_off(self):
        with self.assertRaisesRegex(Exception, 'division by zero'):
            self.run_bbc('ON ERROR PRINT "wrong":END\nON ERROR OFF\nPRINT 1/0')

    def test_error_names(self):
        self.assertEqual(self.run_bbc(
            'ON ERROR PRINT ;ERR;" ";REPORT$:END\nPRINT q'), '26 No such variable\n')
        self.assertEqual(self.run_bbc(
            'ON ERROR PRINT ;ERR;" ";REPORT$:END\nPROCnone'), '29 No such FN/PROC\n')
        self.assertEqual(self.run_bbc(
            'ON ERROR PRINT ;ERR;" ";REPORT$:END\nREAD a'), '42 Out of DATA\n')

    def test_erl_is_zero_without_line_numbers(self):
        self.assertEqual(self.run_bbc('ON ERROR PRINT ;ERL:END\nPRINT 1/0'), '0\n')

    def test_a_new_run_forgets_the_handler(self):
        self.run_bbc('ON ERROR PRINT "old":END\nPRINT "set"')
        with self.assertRaisesRegex(Exception, 'division by zero'):
            self.run_bbc('PRINT 1/0')

    def test_untrapped_error_statement_shows_its_message(self):
        with self.assertRaisesRegex(Exception, 'Custom trouble'):
            self.run_bbc('ERROR 99, "Custom trouble"')

    def test_fn_reading_err_is_not_memoized(self):
        self.assertEqual(self.run_bbc(
            'DEF FNe(x)=ERR+x\nON ERROR PRINT FNe(0):END\nPRINT FNe(0)\nPRINT 1/0'),
            '         0\n        18\n')
