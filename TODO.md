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

### Startup visibility and execution (2026-10-21)

- [x] Add independent saved show-buffer and run-at-startup options in a
  persistent View → Startup Settings window. Keep show-only defaults.
- [x] Run the saved startup source once via the Lisp worker after UI setup,
  even when hidden, with visible errors and existing Stop support.
- [x] Respect explicit files and hidden startup on Restart. Five initial
  regressions failed first; 29 focused startup/file/worker checks now pass.
- [x] Full isolated validation: 516 passed, 4 skipped, 353 subtests passed.

- [x] Python BASIC adapter respects file dialect hints: remove the default
  forced BBC flag; retain an explicit dialect override for adapter callers.
  Regression first failed with --dialect bbc in the captured child arguments.

### Editor save and close fixes (2026-10-21)

- [x] Bind save/close directly on editor widgets and consume shortcuts before
  Tk class bindings. Track dirty state through real Modified events.
- [x] Fix Save As tab lookup/order/name bookkeeping, failed-save identity and
  duplicate basenames; close by tab identity. Preserve tabs on Cancel/failure.
- [x] Reproduce failures first; nine regressions pass, including writing and
  reopening BASIC with REM WAIT intact and saving edits before close.
- [x] Full isolated validation: 509 passed, 4 skipped, 353 subtests passed.

### Language-aware editor execution (2026-10-21)

- [x] Keep BASIC Settings open for visible radio/check state and saved feedback.
  Recognize Python mini_basic's normal console-hold status 10 separately from
  regular Python script exit codes.

- [x] Remove BASIC backend radio buttons and ignore the old saved backend key.
  F5/F6 follow the highlighting language, BASIC defaulting to Lispy mini-basic;
  F7/F8 explicitly run Python mini_basic. Retain location/SDL/output settings.
- [x] Run unsaved Python source in a fresh process, retaining selection source
  lines in tracebacks and using the shared Stop-safe subprocess transport.
- [x] Initial dispatch tests failed before implementation; 39 focused tests pass.
- [x] Full language-dispatch suite: 497 passed, 4 skipped, 351 subtests passed.
  Subsequent settings-feedback and exit-status fixes: 42 focused tests passed.

### BASIC output destination (2026-10-21)

- [x] Add saved Eval → BASIC output → Listener / ANSI terminal selection for
  both BASIC backends. Keep error navigation, timing and Stop; reuse terminal
  hold behaviour. Three new checks failed first; 30 focused checks now pass.

### Exact-argument memoization (2026-10-21)

- [x] Gate automatic BASIC FN memoization and Lisp define-memo on actual
  integer/fraction arguments; bypass floating-point/mixed/non-numeric calls.
- [x] Keep explicit memoize unchanged and expose memoize-exact. Cover argument
  equality collisions (1 versus 1.0), fractions, mixed calls and result types.
- [x] Update both BASIC definition expanders, reader/library integration, help
  and documentation. Regression tests failed before implementation.
- [x] Full validation in an isolated staged copy: 488 passed, 4 skipped,
  351 subtests passed, including the existing recursive Fibonacci regression.

### Editor checking, colouring and indentation (2026-10-21)

- [x] Open/Save dialogs offer combined supported-source, language-specific and
  all-file filters derived from syntax definitions, including uppercase suffixes.

- [x] Add persistent Lispy/Python BASIC backend settings and reuse Python's CLI
  entry point from tools/editor.py. Stream output, support configured project
  and interpreter paths, optional SDL graphics, and child-process cancellation.
- [x] Highlight located BASIC errors and preserve selection/line-number mapping.
  Keep Lisp error highlighting visible until the source changes or is rechecked.
- [ ] Share interpreter-based BASIC pretty-print/renumber and tokenized opening
  with the standalone BASIC editor; do not duplicate or replace its GUI here.

- [x] Keep F7/F8 BASIC execution; add .bas/.basic highlighting with insensitive
  keyword matching and string/REM protection.
- [x] Add Edit menu Lisp reader checks, error navigation, and selection/buffer
  reindent for Lisp and common BASIC blocks. Preserve multiline strings; refuse
  malformed Lisp; group formatting into one undo edit.
- [x] Use lexical Lisp nesting and BASIC blocks for Return indentation.
- [x] Six initial regression tests failed before implementation. Focused
  checks: 40 passed, 4 subtests passed.
- [x] Combined editor/backend validation in an isolated staged copy: 484 passed,
  4 skipped, 341 subtests passed. Real Python mini_basic CLI diagnostics were
  checked with a tiny invalid program; graphical windows were not exercised.

### Reader closing-bracket locations (2026-10-21)

- [x] Retain source positions for closing punctuation and report line/column
  for unexpected closing brackets, including buffer filenames in the GUI.
- [x] Add failing tests first, including comments, multiline strings and plain
  token-list compatibility. Reader/editor checks: 65 passed, 38 subtests passed.

### Editor BASIC execution (2026-10-21)

- [x] F7 runs selected BASIC text or the current line; F8 runs the whole buffer
  through mini-basic without a Lisp wrapper. Shift+F7 inspects a symbol.
- [x] Preserve source quoting, automatic reader import, timing, and errors.
  Four new tests failed before implementation; 19 focused checks now pass.

### Terminal output and buffer timing (2026-10-21)

- [x] Route program output to a real ANSI terminal from Lisp or the GUI while
  retaining the current workspace; keep new output windows open for inspection.
- [x] Add silent loader status and a GUI silent-load action.
- [x] Add optional whole-buffer elapsed timing for both output destinations.
  Timing regressions first failed for successful and aborted runs, then passed.
- [x] Document usage in [TERMINAL_OUTPUT.md](docs/TERMINAL_OUTPUT.md).
- [x] Validate the combined changes: 462 passed, 4 skipped, 337 subtests
  passed in an isolated copy using committed demo launchers. Local timing edits
  to the two native Lisp demo launchers were preserved; their extra output
  makes the unchanged 25-row demo assertions fail in the working checkout.

### mini-basic: fixes before improvements

Progress recorded 2026-10-20. Fix demonstrated errors before adding features.
Compatibility qualification: [the BBCSDL reference checks](basic/reference/README.md)
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
  `basic/reference/`, and verify BBCSDL 1.44a loads it and displays the menu.
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
  reproduction commands are in `basic/reference/README.md`.
- [x] Probe terminators reached without executing their opening statement:
  BBCSDL reports errors for NEXT (32), UNTIL (43), ENDWHILE (46), RETURN (38);
  ENDIF and ENDCASE continue without an error in these probes. Six raw logs
  are retained; no crashes or timeouts occurred.
- [x] Validate the earlier structured EXIT, early FN/ENDPROC return, and
  parameter/LOCAL-restoration tests against BBCSDL. Use normal termination,
  adjusted loop values/conditions, and structured EXIT as the preferred baseline;
  keep cross-boundary jumps separately labelled as diagnostic probes.
- [x] Retain clean structured continuations as an intentional extension. The
  abandoned-FOR/outer-WHILE fixture protects lispy3 continuation, while BBCSDL
  reports error 46. No change to continuation semantics was needed.
- Reference validation (2026-10-23): BBCSDL 1.44a matches ten structured
  EXIT/return/LOCAL fixtures; one separately labelled stack diagnostic differs.
  Sources, expected output, raw logs and a reproducible runner are in
  `basic/reference/structured/` and `basic/reference/runs/structured-2026-10-23/`.
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
`basic/reference/python-mini-basic-control-flow/`. Four representative stored
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

### Explicit libraries and imports

- [x] Test library/export isolation, only/prefix/rename, private macro helpers,
  use-site arguments, mutable private state, includes, cycles and collisions.
- [x] Add mini-basic's opt-in `.sld` manifest without changing legacy load.
- [x] Integrate the NumPy evaluator, completion, help and user documentation.
- [ ] Portable library-aware workspace serialization and reload/unload.
- [ ] Full hygienic syntax-rules; procedural macro temporaries still need gensym.

Library acceptance tests: 14 initial failures established the baseline; 30 tests
now pass, including later regressions for nested macro scope and scoped read/eval.
Full suite: 433 passed, 4 skipped, 324 subtests passed.

### Terminal Mandelbrot examples

- [x] Add native Lisp and mini-basic source with plain/ANSI-colour modes and
  four standalone launchers; retain the existing graphical turtle example.
- [x] Compare small renders with a mathematical reference and each other;
  verify known inside/outside/boundary points, colour reset and 79x25 defaults.
  Four tests / 13 subtests pass after first establishing failures.
- [x] Document run commands and source paths in docs/TERMINAL_MANDELBROT.md.

Terminal Mandelbrot full verification: 444 passed, 4 skipped, 337 subtests
passed. Normal Lisp/plain and NumPy BASIC/colour CLI smoke checks each rendered
79x25 output; colour output ended with the terminal attribute reset.

### Editor destinations, file navigation and real BBCSDL (2026-10-21)

- [x] F6 runs in Listener; Shift+F6 runs in ANSI. Reuse the saved destination
  for form/selection and Python BASIC runs; remove duplicate Settings radios.
- [x] F4, Ctrl+click and context menu open quoted filenames; preserve existing
  unsaved buffers, decode literals without evaluation, and report missing files.
- [x] Add a separate real BBCSDL buffer action and executable/native helper paths.
  Prepare the attributed native loader source; no editor tokenizer is added.
- [x] User saved the native BASRUN.bbc helper; real BBCSDL ran temporary
  source with spaces in its path, printed NATIVE SDL OK 42 and exited 0.
  Executable/helper settings saved locally. EXEC startup probes did not consume queued source.

Validation: exact staged tree passed 525 tests, 4 skipped, 353 subtests.
Native desktop smoke check passed with the user-saved helper on 2026-10-21.

### Tokenised BBC input and Lisp memo verification (2026-10-22)

- [x] Establish five failing editor regressions, then reuse Python mini_basic's
  public binary decoder for .bbc/.BBC input; do not duplicate token tables.
- [x] Open as editable unsaved .bas, retain the origin directory and reject
  text saves to .bbc. Add configured-decoder and clear-error adapter tests.
- [x] Decode the user-saved BASRUN.bbc (28 lines) and reference jumping.bbc
  (118 lines) with the real mini_basic decoder without running their source.
- [x] Confirm Lisp define-memo factorial caching: 60 body evaluations on the
  first (fact 60), none on the second call or cached (fact 59). Plain define
  remains an ordinary procedure; no memoization implementation change needed.

Tokenised input validation: exact staged tree passed 535 tests, 4 skipped,
353 subtests. Local graphics/demo changes remain excluded.

### BBC function terminator diagnostic (2026-10-22)

- [x] Reproduce misleading next-line DEF error after END DEF. Reject this
  non-BBC syntax at its own source line, explain =expression / ENDPROC, and
  retain numbered recursive FN definitions using their normal value return.

### Workspace and module lifecycle (2026-10-22)

- [x] Establish failing state-restoration, stale-variable and fresh-run tests.
- [x] Add independent environments, macros and module registries with exact
  object-preserving push/pop, New, labels, saved depth and managed cleanup.
- [x] Fresh program runs on F6/Shift+F6; current-workspace Eval on F5,
  Ctrl+Shift+Enter and Listener. Preserve buffers and GUI dispatch/Stop hooks.
- [x] Explicit private .lisp modules through import; prefix/only/rename,
  unload/reload, staged binding refresh, dependency checks and cleanup hooks.
- [x] Keep legacy load shared and document side effects, copied references,
  host graphics limits, Python import analogies and other Lisp practices.
- [ ] Disk serialization of workspace stacks and module registries.
- [ ] Automatic dependency-graph reload and host-resource suspension.

Workspace validation: exact staged implementation passed **595 tests**,
**4 skipped**, and **355 subtests**. GUI checks use headless editor harnesses;
no visual desktop smoke test was performed. Local SDL/demo edits were excluded.

### Conditional jumps and local update detection (2026-10-22)

- [x] Reproduce six failures for implicit THEN/ELSE numeric jumps; translate to existing GOTO machinery. BASIC parser/control-flow suite: 98 passed.
- [x] Help > Update detects changed runtime source contents since startup, including local edits, and offers restart even when pull fails. Existing unsaved-buffer safeguards remain.
- [x] Update/startup/control-flow integration: 61 passed, 3 subtests passed.

- [x] Update refreshes externally changed open text buffers without evaluating them; dirty buffers require confirmation. Tokenized imports remain editable copies saved separately.

### BASIC source organization (2026-10-22)

- [x] Move BASIC examples, benchmarks and BBCSDL reference material to basic/.
- [x] Retain Lisp implementation/library files under lisp/ and cross-Lisp backends under compare/.
- [x] Update tests, launchers, documentation links and reproduction commands; preserve historical evidence unchanged.
- Validation: 607 passed, 4 skipped, 355 subtests; 132 moved source/evidence files byte-identical. Both reference command-line tools still show help from their new paths.

### Lispy mini-basic REPL and filename completion (2026-10-22)

- [x] Establish failing tests for private immediate state, program lines and RUN/LIST/NEW/LOAD/SAVE.
- [x] Add BASIC Listener mode, BBC colouring, Stop support, persistent mode settings and BASIC To buffer export. Lisp Listener and Lisp REPL remain available in the same mode menu.
- [x] Add quoted-path completion for BASIC LOAD/SAVE and Lisp load/save/slurp/bbc-load, plus BASIC keyword completion.
- [x] Add standalone python basic_repl.py with readline completion when available.
- [x] Reuse the configured .bbc decoder in the GUI; SAVE refuses tokenised extensions.
- [x] Validate real Tk mode switching and execution in isolated child processes. Full Windows suite: 626 passed, 4 skipped, 355 subtests; WSL: 630 passed, 371 subtests.
- [ ] Multiline immediate-input accumulation; use stored program lines or LOAD/RUN for blocks for now.
- [x] Use project basic/ as the shared default for BASIC LOAD/SAVE and GUI/CLI filename completion; Lisp path resolution remains unchanged. Follow-up: 20 focused tests passed on Windows and WSL.

### WSL pytest discovery (2026-10-22)

- [x] Restrict default discovery to tests/ and exclude the linked Python mini_basic checkout, preventing cross-project collection and unknown-marker warnings.
- Validation: Windows default pytest run: 607 passed, 4 skipped, 355 subtests; WSL Debian existing virtual environment: 611 passed, 371 subtests. Both default collections found exactly 611 lispy3 tests.
