"""A small unit test facility for Lisp code.

    (deftest add-works
      (check (= (+ 1 2) 3))
      (check-equal 4 (+ 2 2))
      (check-error (car 5)))
    (run-tests)

deftest, check, check-equal and check-error are rewritten by lispy3.expand
into calls of the _-prefixed procedures installed here, so the checked
expression is kept as data for the failure report.  Each workspace gets its
own test registry, because install() runs once for every standard_env().

Inside run-tests a failing check is recorded and the test goes on; outside
a test a failing check raises an error, so check also works as an assert.
"""
from __future__ import annotations

import time


def install(env, lisp_str, equal, error_class, is_true):
    tests: dict[str, object] = {}       # name -> zero-argument procedure, in definition order
    state = {'failures': None}          # list while run-tests is running a test

    def show(x):
        return lisp_str(x)

    def fail(message):
        if state['failures'] is None:
            raise error_class(message)
        state['failures'].append(message)
        return False

    def deftest(name, thunk):
        key = show(name)
        tests[key] = thunk
        return None                     # like define, nothing to show

    def check(expr, thunk):
        try:
            value = thunk()
        except Exception as e:          # noqa: BLE001  (Stop is a BaseException and gets past)
            return fail(f'(check {show(expr)}) raised {type(e).__name__}: {e}')
        if not is_true(value):
            return fail(f'(check {show(expr)}) was false')
        return True

    def check_equal(expr, expected, thunk):
        try:
            value = thunk()
        except Exception as e:          # noqa: BLE001
            return fail(f'(check-equal {show(expected)} {show(expr)}) raised {type(e).__name__}: {e}')
        if not equal(expected, value):
            return fail(f'(check-equal {show(expected)} {show(expr)}) got {show(value)}')
        return True

    def check_error(expr, thunk):
        try:
            value = thunk()
        except Exception:               # noqa: BLE001
            return True
        return fail(f'(check-error {show(expr)}) gave {show(value)} with no error')

    def run_tests(*names):
        wanted = [show(n) for n in names] or list(tests)
        missing = [n for n in wanted if n not in tests]
        if missing:
            raise error_class('run-tests: no test named ' + ', '.join(missing))
        started = time.perf_counter()
        failed = []
        for name in wanted:
            state['failures'] = failures = []
            try:
                tests[name]()
            except Exception as e:      # noqa: BLE001
                failures.append(f'error {type(e).__name__}: {e}')
            finally:
                state['failures'] = None
            if failures:
                failed.append(name)
                print(f'FAIL {name}')
                for message in failures:
                    print(f'  {message}')
        elapsed = time.perf_counter() - started
        count = len(wanted)
        plural = '' if count == 1 else 's'
        if failed:
            print(f'{len(failed)} of {count} test{plural} FAILED ({elapsed:.3f} s): {" ".join(failed)}')
        else:
            print(f'{count} test{plural} passed ({elapsed:.3f} s)')
        return not failed

    def clear_tests():
        tests.clear()
        return []

    def test_names():
        return list(tests)

    env.update({
        '_deftest': deftest,
        '_check': check,
        '_check-equal': check_equal,
        '_check-error': check_error,
        'run-tests': run_tests,
        'clear-tests': clear_tests,
        'test-names': test_names,
    })
