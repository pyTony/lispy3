"""Console INPUT behavior through the actual BASIC reader and runtime."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from test_mini_basic_reader import ReaderTestCase


class BasicInputTest(ReaderTestCase):
    def input_bbc(self, source, *replies):
        with patch('builtins.input', side_effect=replies) as read:
            output = self.run_bbc(source)
        self.assertEqual(read.call_count, len(replies))
        return output

    def test_enter_pause_and_following_output(self):
        self.assertEqual(self.input_bbc(
            'INPUT "PRESS ENTER", L$\nPRINT "done"', ''), 'PRESS ENTER?done\n')

    def test_prompt_separators_and_suppressed_question_mark(self):
        for separator, question in [(',', '?'), (';', '?'), ('', '')]:
            with self.subTest(separator=separator):
                self.assertEqual(self.input_bbc(
                    f'INPUT "Name: "{separator} name$\nPRINT name$', 'Ada'),
                    'Name: '+question+'Ada\n')

    def test_comma_values_quoted_strings_and_integer_coercion(self):
        self.assertEqual(self.input_bbc(
            'INPUT n%,s$,x\nPRINT ;n%;"/";s$;"/";x',
            '3.9,"hello, world",-2.5'), '?3/hello, world/-2.5\n')

    def test_missing_values_continue_on_next_line(self):
        self.assertEqual(self.input_bbc(
            'INPUT a,b\nPRINT ;a+b', '2', '3'), '??5\n')

    def test_empty_input_and_hexadecimal_numeric_value(self):
        self.assertEqual(self.input_bbc(
            'INPUT n,s$,h\nPRINT ;n;"/[";s$;"]/";h', ',,&FF'), '?0/[]/255\n')

    def test_unterminated_quoted_reply_reports_input_error(self):
        with patch('builtins.input', return_value='"unfinished'):
            with self.assertRaisesRegex(ValueError, 'INPUT:'):
                self.run_bbc('INPUT s$')

    def test_eof_is_reported_without_retrying_forever(self):
        with patch('builtins.input', side_effect=EOFError):
            with self.assertRaises(EOFError):
                self.run_bbc('INPUT s$')

    def test_primes_visual_runs_with_enter_pause_enabled(self):
        source = (Path(__file__).resolve().parents[1]/'basic/examples/primes_visual.bas').read_text()
        source = source.replace('L = 1000', 'L = 30')
        self.assertIn('50 INPUT "PRESS ENTER", L$', source)
        output = self.input_bbc(source, '')
        self.assertIn('9 primes.', output)
        self.assertIn('PRESS ENTER?', output)

    def test_numeric_input_uses_value_prefix_without_evaluating_code(self):
        self.assertEqual(self.input_bbc(
            'INPUT a,b,c\nPRINT ;a;"/";b;"/";c',
            '12tail,1+9,not-a-number'), '?12/1/0\n')

    def test_input_line_preserves_spaces_commas_and_quotes(self):
        self.assertEqual(self.input_bbc(
            'INPUT LINE "Text: " text$\nPRINT "[";text$;"]"',
            '  hello, "world"  '), 'Text: [  hello, "world"  ]\n')

    def test_input_array_element_and_local_variable(self):
        self.assertEqual(self.input_bbc(
            'DIM a%(2)\nINPUT a%(1)\nPROCask\nPRINT ;a%(1)\nEND\n'
            'DEF PROCask\nLOCAL n$\nINPUT n$\nPRINT n$\nENDPROC',
            '7.9', 'Ada'), '??Ada\n7\n')

    def test_line_input_rejects_numeric_target_with_location(self):
        with self.assertRaisesRegex(Exception, r'line 2:.*string'):
            self.expand('REM header\nINPUT LINE n')

    def test_standalone_cli_input_consumes_reply_not_as_a_command(self):
        result = subprocess.run([sys.executable, 'basic_repl.py'],
            input='INPUT "Name: " n$\nAda\nPRINT n$\nQUIT\n',
            capture_output=True, text=True, timeout=15,
            cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Name: ', result.stdout)
        self.assertIn('Ada\n', result.stdout)
        self.assertNotIn('Error:', result.stdout)
