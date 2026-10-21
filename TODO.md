# TODO

Most of the language items below came in with the Gemini Argon version (October 2026). The manual (docs/) still describes several of them as TO BE IMPLEMENTED and needs updating.

Features the manual marks **TO BE IMPLEMENTED** (see [docs/LISPY_BY_EXAMPLE.md](docs/LISPY_BY_EXAMPLE.md) for today's workarounds). When one is done, add it to `HELP_TOPICS` in `lispy3.py` and to [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md), and remove its TO BE IMPLEMENTED notes.

Many of these already exist, as small pattern-matching Python 3.10 code close to ours, in Luciano Ramalho's [fluentpython/lispy](https://github.com/fluentpython/lispy) (variations of Norvig's `lis.py`, the same ancestor as Lispy). Items marked *(ref: ...)* point to the file to read:

- `original/py3.10/lis.py`: Norvig's `lis.py` with type hints and `match`/`case`
- `mylis/mylis_2/lis.py`: adds `set!`, `cond`, `and`, `or` and proper tail calls
- `mylis/mylis_3/environ.py`: variadic `+` and comparisons, `modulo`, `quotient`

## Language

- [x] `cond` for a chain of tests *(ref: mylis_2 `cond_form`)*
- [x] `and` / `or`, short-circuit, so they must be special forms *(ref: mylis_2 `and_form`, `or_form`)*
- [x] Macros: `define-macro`, quasiquote `` ` `` with `,` and `,@`, `gensym` (`eval` exists) *(ref: Norvig `original/norvig/lispy.py`, `expand` and `expand_quasiquote`)*
- [x] `(define (f x) body)` shorthand *(ref: py3.10 `lis.py`, `case ['define', [Symbol(name), *parms], *body]`)*
- [x] Several body expressions in `lambda` and `let` without `begin` *(ref: py3.10 `lis.py`, `case ['lambda', [*parms], *body]`)*
- [x] Proper tail calls, so tail recursion is not limited to about 200 calls *(ref: mylis_2 `evaluate`, the `while True` loop with `TCO_ENABLED`)*
- [x] `try` / `error` to raise and catch errors inside a program

## Numbers

- [x] `+ - * /` with any number of arguments, e.g. `(+ 1 2 3)` *(ref: mylis_3 `environ.py`)*
- [x] `<`, `=`, ... comparing more than two values, e.g. `(< 1 2 3)` *(ref: mylis_3 `variadic_comparison`)*
- [x] `modulo` and `quotient` on whole numbers (today only `fmod`, which gives a decimal) *(ref: mylis_3 `environ.py`)*
- [x] More whole-number procedures: `div`, `mod`, `divmod`, `remainder`, `even?`, `odd?`, `zero?`, `positive?`, `negative?`, `integer?`, `exact`, `inexact`, `number->string` with a base

## Lists

- [x] `reverse`, `nth`, `last`, `range`
- [x] `reduce` / `fold`, `apply`, `sort`, `member` *(ref: `apply` in py3.10 `lis.py`; `member` in `mylis/mylis_2/examples/member.scm`)*
- [x] `append` with any number of lists *(ref: py3.10 `lis.py`)*
- [x] `list?`, `procedure?`, `eq?`, `equal?` tests *(ref: py3.10 `lis.py`)*
- [x] `for-each` and a counting loop (`dotimes` or `for`)

## Strings

- [x] `substring`, `string-ref`, `upcase`, `downcase`, `split`, `list->string`
- [x] `string->number`
- [x] `str` should return a real string, so `(= (str 12) "12")` is true
- [x] More string escapes: `\r`, hex and Unicode (`\x41;`, `\u00e4`)
- [x] More character names: `#\return`, `#\nul`, `#\x41`
- [x] String formatting: `format`, or `str` taking several values

## Maps

- [x] `assoc`, `dissoc`, `keys`, `vals`, `contains?`

## Tests

### mini-basic: fixes before improvements

Progress recorded 2026-10-20. Fix demonstrated errors before adding features.
Compatibility qualification: [the BBCSDL reference checks](compare/reference/README.md)
now record all 14 observations on version 1.44a. The exact numeric-label cases
match the expected normal outputs or missing-target error; this does not imply
compatibility for arbitrary jumps or abandoned loop-stack continuations.
Use red → green → refactor: first reproduce the required behavior in an ordinary
failing test, implement the smallest correct fix, then retain the passing test.
Do not skip or mark pending acceptance tests as expected failures.

- [x] Add `tests/test_mini_basic_tdd.py` with output-based regression and acceptance tests.
- [x] Verify the red baseline: **7 failed, 3 passed**. Three failures reproduce
  nested-label lookup errors; four cover missing subroutine features.
- [x] Verify existing mini-basic tests: **55 passed**.
- [x] Prepare one plain-text BBCSDL reference program for manual tokenised save.
- [x] Receive the user's tokenised `jumping.bbc`, preserve an unchanged copy in
  `compare/reference/`, and verify BBCSDL 1.44a loads it and displays the menu.
  Individual case observations are recorded in the reference README.
- [x] Run all 14 BBCSDL cases in isolated processes and preserve raw logs and
  JSON results: **13 normal outputs, 1 expected error, no crashes or timeouts**.
  Missing-target case: **ERR 41, No such line, at line 10020**.
- [x] Consult the shared BBCSDL/BB4W manual's structure limitations. Document
  that case 5's immediate exit does not verify loop-stack cleanup; numeric CASE
  success does not verify symbolic labels. The numbered-WHEN parser discrepancy
  is confirmed against BBCSDL by case 9.
- [x] Probe small loops after the GOTO exit on BBCSDL 1.44a: a fresh FOR and a
  fresh WHILE succeed; continuing an enclosing WHILE after abandoning its inner
  FOR reports **ERR 46, Not in a WHILE loop, at line 5082**. Raw logs and
  reproduction commands are in `compare/reference/README.md`.
- [x] Probe terminators reached without executing their opening statement:
  BBCSDL reports errors for NEXT (32), UNTIL (43), ENDWHILE (46), RETURN (38);
  ENDIF and ENDCASE continue without an error in these probes. Six raw logs
  are retained; no crashes or timeouts occurred.
- [ ] Validate the earlier structured EXIT, early FN/ENDPROC return, and
  parameter/LOCAL-restoration tests against BBCSDL. Use normal termination,
  adjusted loop values/conditions, and structured EXIT as the preferred baseline;
  keep cross-boundary jumps separately labelled as diagnostic probes.
- [ ] Decide whether lispy3 should reproduce that stack error or document an
  intentional extension; then add the corresponding failing acceptance test
  before changing continuation semantics.
- [x] **Priority 1 — fix nested-label GOTO lookup.** Jumps within active
  structured bodies now resolve local labels, preserving loop and branch
  continuations. Unmatched targets propagate to enclosing active bodies;
  missing labels still report the target at the program boundary.
- [x] Expand `NestedJumpRegressionTest` to **10 passing tests**, covering `FOR`,
  `WHILE`, `IF` / `ELSE`, `REPEAT`, `CASE`, backward jumps, `ON … GOTO`, jumps
  to enclosing bodies, exits to program labels, and unknown-label errors.
- [x] Rerun existing mini-basic tests and the three controls: **58 passed**.
  Full suite: **353 passed, 4 skipped, 316 subtests passed**, with **4 failures**
  exclusively in the pending `SubroutineAcceptanceTest` features. The initial
  sandbox run encountered unrelated temporary-file permission errors; the full
  verification above was rerun outside the sandbox.
- [x] Fix the numbered `WHEN` reader error with three red-first regressions:
  exact BBCSDL case 9, nested/multiple-value clauses, and DATA/RESTORE label
  preservation (including OTHERWISE and ENDCASE). Focused mini-basic suite:
  **71 passed**, with only the **4 pending subroutine failures** remaining.
- [x] Full regression after the numbered-CASE fix: **356 passed, 4 skipped,
  316 subtests passed**, with the same **4 pending subroutine failures**.
- [x] Clarify that the requested historical stack/exit audit concerns the
  **Python mini_basic suite**. Add an exporter that captures actual run inputs
  and observed output without editing the external tests. Four selected
  control-flow test methods pass and yield **18 concrete BASIC programs**;
  a four-case representative menu is prepared for one manual tokenised save.
- [x] Run the four representative Python-test stored programs on BBCSDL after
  the user's native save: both `bbc` cases match exactly; both `mini` cases have
  matching values with nine extra leading spaces in SDL. No errors or timeouts.
  Python had normalised WEND before capture; these observations concern stored
  programs, not unchanged original inputs or all Python assertions/mocks.
- [x] Extend future exports to retain original set_program_line submissions as
  `.input.bas` when available, separately from normalised stored source.
- [x] **Priority 2 — subroutine improvements, after known errors are fixed.**
  Implement `GOSUB` / `RETURN`, including same-line continuation, nested calls,
  and calls within `FOR`, using `SubroutineAcceptanceTest`.
- [x] Implement `ON … GOSUB` with one-based selection and return continuation.
- [x] Turn all four original subroutine tests green; extend coverage to 17
  subroutine/ON-branch tests for exact continuation, nested calls, loops,
  variable/symbolic targets, PROC/FN boundaries, and cleanup after errors/END.
- [x] Confirm selector zero and too-large selectors raise BBCSDL error 40
  (ON range), and ELSE supplies a fallback. Add red-first range regressions;
  fix the shared ON GOTO/GOSUB branch generation.
- [x] Merge approved PR #46 into this branch. Full suite after subroutine work:
  **380 passed, 4 skipped, 319 subtests passed, no failures**.

#### Ordered continuation plan (2026-10-20)

Each implementation step starts with a failing behavior test, followed by the
smallest fix and regression checks. Reference observations and documented
restrictions are separate evidence: do not infer stack safety from normal output.
The order below governs the remaining work above.

1. **Fix the confirmed numbered-CASE reader error.** Reproduce BBCSDL case 9
   directly in a failing lispy3 test, retaining numbers on WHEN, OTHERWISE and
   ENDCASE lines. Cover multiple branches and nesting, fix label handling at
   clause/block boundaries, and check that line labels remain available to
   DATA/RESTORE and valid jumps. Done when the numeric reference case and existing
   CASE/reader tests pass without changing unrelated control-flow semantics.
2. **Define the control-flow compatibility contract.** Keep structured execution,
   normal termination, adjusted variables/conditions and EXIT as the supported
   baseline. Record within-body GOTO as observed compatibility behavior. Decide
   explicitly how to handle inactive-body entry, mismatched terminators and
   abandoned-loop continuation before changing their behavior. Do not silently
   weaken structural checks or emulate stack corruption merely because SDL
   tolerates some jumps. Any intentional cleanup extension must be documented.
   Done when each diagnostic probe is classified and has an agreed test outcome;
   this policy decision is still pending.
3. **Audit existing exit and restoration behavior against BBCSDL.** Extend the
   reference cases for EXIT FOR/REPEAT/WHILE, early ENDPROC/FN return from loops,
   nested calls, and parameter/LOCAL restoration. Test useful continuation after
   each exit, not just printing and stopping. Include runtime errors and repeated
   runs to detect leaked state. Fix confirmed discrepancies with tests first;
   document cases where error cleanup intentionally differs. Reuse native
   fixtures; any general tokenised-file support belongs in mini-basic, not a
   separate ad hoc tokenizer. Done when the existing relevant tests have a
   recorded SDL result or an explicit limitation/extension classification.
4. **Implement GOSUB / RETURN incrementally.** Turn the four existing subroutine
   acceptance tests green in order: same-line return, nested calls, calls from
   a FOR body, then ON GOSUB. Before adding the return stack, make return addresses
   represent the exact following statement, not just the next line/segment.
   Test missing targets and RETURN without GOSUB; verify procedure boundaries,
   loop continuation and stack reset between runs. Confirm ON GOSUB range and
   ELSE behavior on SDL before defining those additional expectations. Done when
   the acceptance tests and error-path tests pass and no known failures remain
   in the full suite (environmental skips are reported separately).
5. **Consolidate the supported release baseline.** Update README/changelog and
   feature coverage, keep native fixtures/logs reproducible, and rerun the full
   lispy3 suite plus applicable comparison programs. State which extensions are
   lispy3-only; SBCL/Clojure currently lack the Step 3 extensions, so their parity
   must not be implied. Preserve the plain-macro fast path for jump-free programs.
6. **Then select the next feature batch.** Candidate console features are INPUT,
   RND and further TIME compatibility, followed by file I/O as needed by real example programs. Choose
   one small behavior at a time, establish its SDL result, write the failing
   acceptance test, implement it, and retain the regression. Graphics, broad
   dialect expansion and a general tokenizer are deferred from the current fix
   and subroutine milestones.

TIME progress: the existing terminal `mandelbrot2.bas` exposed a confirmed bug:
TIME was an ordinary variable and always reported zero after TIME=0. Eight
clock tests were added first (seven failed, one passed), then the assignable
centisecond clock was implemented. It supports LET and compound updates,
persists between runs, and prevents memoization of clock-dependent FN results.
The unchanged demo rendered 25 rows and reported 1.03 seconds (outer load/run:
1.205 seconds). Full suite: 388 passed, 4 skipped, 319 subtests passed.
TIME starts when the library loads; BBC's 32-bit wrap and TIME$ remain pending.
This implementation is for lispy3; backend parity is not implied.

Steps 1 and 4 are complete. The broader compatibility-policy/audit work in steps
2-3 and release/next-feature planning in steps 5-6 remain pending. The user's requested Python-suite
audit now has actual exported programs and a representative native menu in
`compare/reference/python-mini-basic-control-flow/`. Four representative stored
programs have recorded BBCSDL results; the broader audit remains pending.
The earlier `bbcsdl-structured-checks.bas` is a
separate lispy3-derived audit source, not a substitute for the Python test cases.
Runtime-error restoration still needs separate probes.
Prefer small user-executed preparation tasks over expensive UI automation when
they do not block independent progress.

Commands (from the repository root):

```powershell
# Completed fix: ten passing regression tests
python -m pytest tests/test_mini_basic_tdd.py::NestedJumpRegressionTest -q
# Existing behavior must remain green
python -m pytest tests/test_mini_basic.py tests/test_mini_basic_reader.py tests/test_mini_basic_tdd.py::ExistingExtensionsTest -q
# Implemented acceptance tests: now green
python -m pytest tests/test_mini_basic_tdd.py -q
# Full suite: now green (optional external-Lisp checks may skip)
python -m pytest tests -q
```

Implementation status: **nested-label GOTO, numbered CASE, and GOSUB/RETURN/ON
GOSUB are implemented**. All current acceptance tests pass; none are skipped or
marked expected failures to hide unfinished work.
This fix covers jumps within or out of already active bodies; entry into an
inactive branch or loop is outside this change. A separate parser issue with
numbered `WHEN` lines was confirmed against BBCSDL and is now fixed.

- [x] Regression tests from Norvig's lispy.html and his `lis_tests` (`tests/test_norvig.py`, run `python -m unittest`)
- [x] `equal?`, `eq?`, `expt`, `apply`, `list?`, `procedure?`, `print` and many-list `map` are in; their Norvig tests are now normal tests (`NorvigStandardEnvTest`)
- [x] Tests for the Gemini Argon additions and the features restored after it (`tests/test_gemini_features.py`)
- [x] Tests for Lispy's own additions (strings, maps, vectors, `while`, save/load, the example programs) (`tests/test_lispy_additions.py`)
- [x] Every ticked item above has examples in `tests/test_todo.py`; ticking a box without adding them fails the tests

### Terminal paste input

- [x] Reproduce multi-form input loss and GNU paste configuration with failing
  regressions (five failed, two passed before implementation).
- [x] Enable GNU readline bracketed paste and evaluate all submitted forms in
  order; reject malformed trailing syntax before any form runs.
- [x] Seven regressions pass. Real GNU-readline pseudo-terminal check under WSL
  verified a two-form paste returns 42. Document code-only pasting and Enter.
  Full suite: 410 passed, 4 skipped, 324 subtests passed.


### mini-basic user documentation

- [x] Start `docs/MINI_BASIC.md`: loading, supported subset, control-flow limits,
  TIME, external terminal Mandelbrot and existing ANSI escape output.
- [x] Add tested terminal macros and BASIC reader syntax: CLS, COLOUR/COLOR,
  TAB(x,y), a bounded VDU text decoder and separate raw ANSI output.
  Fifteen tests cover exact bytes, columns, split VDU parameters, errors and
  non-memoized terminal effects. Raw ANSI cursor changes remain untracked;
  full VDU/viewport emulation and semicolon word syntax remain pending.

ANSI/VDU validation: 15 targeted tests and 5 subtests passed; full suite
403 passed, 4 skipped, 324 subtests passed. Desktop rendering remains a manual
terminal check; tests verify exact emitted controls and column behavior.
