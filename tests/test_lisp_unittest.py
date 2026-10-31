"""Tests for unit test runs: Lisp (deftest/check/run-tests) and the Machine's Run tests.

Run:  python -m unittest discover tests
"""
import contextlib
import io
import os
import subprocess
import tempfile
import textwrap
import unittest
from unittest.mock import Mock

from support import LispyTestCase, lispy3
from test_machine_eval_buffer import _FakeMachine
from test_machine_args import machine


class LispTestFormsTest(LispyTestCase):

    def run_tests(self, *sources):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = self.ev_all(*sources)
        return result, out.getvalue()

    def test_passing_tests_give_true_and_a_summary(self):
        result, out = self.run_tests(
            '(define (sq x) (* x x))',
            '(deftest squares (check (= (sq 3) 9)) (check-equal 16 (sq 4)) (check-error (/ 1 0)))',
            '(deftest more (check-equal (list 1 2) (list 1 2)))',
            '(run-tests)')
        self.assertIs(result, True)
        self.assertIn('2 tests passed', out)
        self.assertNotIn('FAIL', out)

    def test_failures_are_reported_and_the_test_goes_on(self):
        result, out = self.run_tests(
            '(deftest broken (check (= 1 2)) (check-equal 3 (+ 1 1)) (check-error (+ 1 1)) (check (car (list))))',
            '(deftest fine (check #t))',
            '(run-tests)')
        self.assertIs(result, False)
        self.assertIn('FAIL broken', out)
        self.assertIn('(check (= 1 2)) was false', out)
        self.assertIn('(check-equal 3 (+ 1 1)) got 2', out)
        self.assertIn('(check-error (+ 1 1)) gave 2 with no error', out)
        self.assertIn('(check (car (list))) was false', out)
        self.assertIn('1 of 2 tests FAILED', out)
        self.assertNotIn('FAIL fine', out)

    def test_an_error_in_a_test_fails_only_that_test(self):
        result, out = self.run_tests('(deftest crashes (error "boom") (check #t))',
                                     '(deftest fine (check #t))', '(run-tests)')
        self.assertIs(result, False)
        self.assertIn('FAIL crashes', out)
        self.assertIn('boom', out)
        self.assertIn('1 of 2 tests FAILED', out)

    def test_a_check_that_raises_is_a_failure(self):
        _, out = self.run_tests('(deftest t1 (check (error "bad")))', '(run-tests)')
        self.assertIn('(check (error "bad")) raised', out)

    def test_run_tests_by_name_and_names(self):
        result, out = self.run_tests('(deftest a (check #t))', '(deftest b (check #f))', "(run-tests 'a)")
        self.assertIs(result, True)
        self.assertIn('1 test passed', out)
        self.assertEqual(lispy3.lisp_str(self.ev('(test-names)')), '(a b)')
        with self.assertRaises(lispy3.LispyError):
            self.ev("(run-tests 'nope)")

    def test_redefining_a_test_replaces_it(self):
        result, out = self.run_tests('(deftest a (check #f))', '(deftest a (check #t))', '(run-tests)')
        self.assertIs(result, True)
        self.assertIn('1 test passed', out)

    def test_clear_tests(self):
        result, out = self.run_tests('(deftest a (check #f))', '(clear-tests)', '(run-tests)')
        self.assertIs(result, True)
        self.assertIn('0 tests passed', out)

    def test_check_outside_a_test_is_an_assert(self):
        self.assertIs(self.ev('(check (= 1 1))'), True)
        with self.assertRaises(lispy3.LispyError) as caught:
            self.ev('(check (= 1 2))')
        self.assertIn('(check (= 1 2)) was false', str(caught.exception))
        self.assertEqual(self.show('(try (check-equal 1 2) (catch e "caught"))'), '"caught"')

    def test_tests_belong_to_their_workspace(self):
        self.run_tests('(deftest a (check #t))')
        lispy3.workspaces.push('tests')
        try:
            self.assertEqual(lispy3.lisp_str(lispy3.eval_exp(lispy3.parse('(test-names)'), lispy3.global_env)), '()')
        finally:
            lispy3.workspaces.pop()
        self.assertEqual(lispy3.lisp_str(self.ev('(test-names)')), '(a)')

    def test_bad_forms_are_syntax_errors(self):
        for source in ('(deftest)', '(check)', '(check 1 2)', '(check-equal 1)'):
            with self.subTest(source=source), self.assertRaises(SyntaxError):
                self.ev(source)

    def test_names_are_in_help_and_completion(self):
        names = lispy3.completion_candidates()
        for name in ('deftest', 'check', 'check-equal', 'check-error', 'run-tests', 'clear-tests'):
            self.assertIn(name, names)
        topics = {name for entries in lispy3.HELP_TOPICS.values() for name, _ in entries}
        for name in ('deftest', 'check', 'check-equal', 'check-error', 'run-tests'):
            self.assertIn(name, topics)


class _Tab:
    def __init__(self, name, content, path=None, language='Lisp'):
        self.name, self.content, self.path, self.dirty = name, content, path, False
        self.language = Mock()
        self.language.name = language

    def get_content(self):
        return self.content


class MachineRunTestsTest(unittest.TestCase):

    def setUp(self):
        from support import fresh_global_env
        fresh_global_env()

    def test_lisp_buffer_runs_its_deftests_in_a_fresh_workspace(self):
        app = Mock()
        app._busy.return_value = False
        app.current_tab.return_value = _Tab('t.lisp', '(deftest a (check #t))')
        machine.LispMachine.run_buffer_tests(app)
        app.eval_buffer.assert_called_once_with(terminal=False, fresh=True, echo='off', after='(run-tests)')

    def test_eval_buffer_runs_the_after_form(self):
        app = _FakeMachine('(deftest a (check (= 1 1)))\n(deftest b (check-equal 2 (+ 1 2)))')
        machine.LispMachine.eval_buffer(app, echo='off', after='(run-tests)')
        out = ''.join(app.lines)
        self.assertIn('FAIL b', out)
        self.assertIn('1 of 2 tests FAILED', out)
        self.assertNotIn('USER>', out)

    def test_other_languages_get_a_note(self):
        app = Mock()
        app._busy.return_value = False
        app.current_tab.return_value = _Tab('t.bas', '10 PRINT 1', language='BBC BASIC')
        machine.LispMachine.run_buffer_tests(app)
        self.assertIn('Run tests works on', app.listener_write.call_args[0][0])


PASSING = textwrap.dedent('''\
    import unittest
    class T(unittest.TestCase):
        def test_ok(self):
            self.assertEqual(1 + 1, 2)
''')
FAILING = PASSING + '''    def test_bad(self):
        self.assertEqual(1, 2)
'''


class PythonTestRunsTest(unittest.TestCase):

    def test_target_inside_a_package_uses_the_dotted_name(self):
        with tempfile.TemporaryDirectory() as root:
            pkg = os.path.join(root, 'pkg', 'tests')
            os.makedirs(pkg)
            for folder in (os.path.join(root, 'pkg'), pkg):
                open(os.path.join(folder, '__init__.py'), 'w').close()
            path = os.path.join(pkg, 'test_x.py')
            self.assertEqual(machine.python_test_target(path), (root, 'pkg.tests.test_x'))
            plain = os.path.join(root, 'test_y.py')
            self.assertEqual(machine.python_test_target(plain), (root, 'test_y'))
            command, cwd, _ = machine.python_test_command(folder=pkg)
            self.assertEqual(cwd, root)
            self.assertEqual(command[-4:], ['-s', os.path.abspath(pkg), '-t', root])

    def test_command_runs_unittest(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'test_sample.py')
            with open(path, 'w') as f:
                f.write(FAILING)
            command, cwd, env = machine.python_test_command(path=path)
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('test_bad', result.stderr)
            self.assertIn('FAILED (failures=1)', result.stderr)

    def _machine(self, tab):
        app = _FakeMachine('')
        app.tab = tab
        app._save_tab_to_path = Mock(return_value=True)
        return app

    def test_untitled_python_buffer_runs_from_a_temporary_copy(self):
        app = self._machine(_Tab('*scratch*', PASSING, language='Python'))
        machine.LispMachine._run_python_tests(app, app.tab)
        out = ''.join(app.lines)
        self.assertIn('test_ok', out)
        self.assertIn('Python unit tests all passed', out)

    def test_saved_python_file_is_saved_then_run(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'test_saved.py')
            with open(path, 'w') as f:
                f.write(FAILING)
            tab = _Tab('test_saved.py', FAILING, path=path, language='Python')
            tab.dirty = True
            app = self._machine(tab)
            machine.LispMachine._run_python_tests(app, tab)
            app._save_tab_to_path.assert_called_once_with(tab, path)
            out = ''.join(app.lines)
            self.assertIn('test_bad', out)
            self.assertIn('Python unit tests FAILED', out)

    def test_folder_run_discovers_every_test_file(self):
        with tempfile.TemporaryDirectory() as root:
            for name, text in (('test_one.py', PASSING), ('test_two.py', PASSING)):
                with open(os.path.join(root, name), 'w') as f:
                    f.write(text)
            tab = _Tab('test_one.py', PASSING, path=os.path.join(root, 'test_one.py'), language='Python')
            app = self._machine(tab)
            machine.LispMachine._run_python_tests(app, tab, folder=True)
            out = ''.join(app.lines)
            self.assertIn('Ran 2 tests', out)
            self.assertIn('all passed', out)


if __name__ == '__main__':
    unittest.main()
