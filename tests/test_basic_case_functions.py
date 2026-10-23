"""mini_basic string-case compatibility extensions used by ELIZA/BETH."""
from unittest.mock import patch
from test_mini_basic_reader import ReaderTestCase


class CaseFunctionTest(ReaderTestCase):
    def test_upper_and_lower_strings(self):
        self.assertEqual(self.run_bbc('PRINT UCASE$("My LLM always makes mistakes"):PRINT LCASE$("ABC xyz 123!")'),
                         'MY LLM ALWAYS MAKES MISTAKES\nabc xyz 123!\n')

    def test_empty_unicode_and_source_preservation(self):
        self.assertEqual(self.run_bbc('s$="äÖß":PRINT UCASE$(s$);"/";LCASE$(s$);"/";s$:PRINT "[";UCASE$("");"]"'),
                         'ÄÖSS/äöß/äÖß\n[]\n')

    def test_string_type_survives_composition(self):
        self.assertEqual(self.run_bbc('PRINT LEFT$(UCASE$("hello"),2)+LCASE$("LLO"):PRINT LEN(UCASE$("abc"))'),
                         'HEllo\n         3\n')

    def test_eliza_style_input_normalization_and_exit(self):
        source='10 INPUT I$\n20 I$=" "+I$+"  "\n30 I$=UCASE$(I$)\n40 IF MID$(I$,2,4)="SHUT" THEN PRINT "SHUT UP...":END\n50 PRINT I$\n60 GOTO 10'
        with patch('builtins.input',side_effect=['My LLM always makes mistakes','shut up']) as read:
            output=self.run_bbc(source)
        self.assertEqual(read.call_count,2)
        self.assertEqual(output,'? MY LLM ALWAYS MAKES MISTAKES  \n?SHUT UP...\n')

    def test_numeric_arguments_have_clear_errors(self):
        for name in ('UCASE$','LCASE$'):
            with self.subTest(name=name), self.assertRaisesRegex(Exception, r'expected a string'):
                self.run_bbc('PRINT '+name+'(123)')

    def test_wrong_argument_counts_are_rejected(self):
        for call in ('UCASE$()','LCASE$("a","b")'):
            with self.subTest(call=call), self.assertRaises(Exception):
                self.run_bbc('PRINT '+call)
