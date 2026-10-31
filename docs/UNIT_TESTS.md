# Unit tests

Lispy Machine runs unit tests for Lisp and Python buffers. Choose
**Eval → Run tests in buffer** or press **Ctrl+F6**. The results appear in
the Listener.

## Lisp tests

```lisp
(define (sq x) (* x x))

(deftest squares
  (check (= (sq 3) 9))
  (check-equal 16 (sq 4))
  (check-error (/ 1 0)))

(deftest lists
  (check-equal '(1 4 9) (map sq '(1 2 3))))
```

Ctrl+F6 runs the buffer silently in a fresh workspace, then runs `(run-tests)`:

```
FAIL lists
  (check-equal (1 4 9) (map sq '(1 2 3))) got (1 4 10)
1 of 2 tests FAILED (0.001 s): lists
```

| Form | Meaning |
|---|---|
| `(deftest name body...)` | Define a test; defining the same name again replaces it |
| `(check exp)` | Passes when exp is true; fails when it is `#f`, `()` or raises an error |
| `(check-equal expected exp)` | Passes when `(equal? expected exp)` |
| `(check-error exp)` | Passes when exp raises an error |
| `(run-tests)` | Run every test, print FAIL lines and a summary, give `#t` when all passed |
| `(run-tests 'a 'b)` | Run only the named tests |
| `(test-names)` / `(clear-tests)` | List / forget the tests of the current workspace |

A failing check inside a test is reported and the test goes on to its next
check. An error in the test body ends that test only. Outside a test, a failing
`check` raises an error, so it also works as an assert; `try` can catch it.

Each workspace keeps its own tests, so a fresh run never sees tests left over
from an earlier buffer. You can also type `(run-tests)` in the Listener after
F6 or Ctrl+Shift+Enter.

## Python tests

In a Python buffer, Ctrl+F6 runs `python -m unittest -v` on the file in a
separate process. A saved buffer with changes is saved first. An untitled
buffer runs from a temporary copy. When the file is in a package (folders with
`__init__.py`), it runs from the folder above the package, so imports such as
`from tests.support import ...` work.

**Eval → Run Python tests in buffer's folder** runs
`python -m unittest discover` on every `test*.py` in the buffer's folder.
On the dev branch, open any file in Lispy's `tests/` folder and use it to run
Lispy's own suite.

Stop (Ctrl+Break) ends a Python test run.
