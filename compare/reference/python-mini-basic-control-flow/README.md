# Programs extracted from the Python mini_basic tests

Source repository: `C:\Users\admin\mini_basic`.
Source module: `test/test_control_flow.py`. Captured 2026-10-20.
These are tests of the Python interpreter, not lispy3's test suite.

Four selected pytest methods passed with their original assertions, exporting
18 actual BASIC executions (including concrete Hypothesis-generated examples).
The exporter observes `BASICInterpreter.run()`; it does not edit those tests or
replace their assertions. Hypothesis databases and Python/pytest cache writes
are kept out of the source repository by the runner configuration.

Each run has a stored-program `.bas`, `.stdout.txt`, and `.stderr.txt` file. `manifest.json`
records the originating pytest node, Python test source, dialect, exceptions,
and test phase outcomes. Captured Python output is **not a BBCSDL golden**.

## One file to save in BBCSDL

Open `representative-menu.bas` and save it tokenised as
`representative-menu.bbc`. It contains one concrete example from each method:

| Menu case | Python test | Original dialect | Observed Python output |
|---|---|---|---|
| 1 | TestExitLeavesUnclosedIfBlock.test_exit_for_then_unrelated_endif_targets_its_own_line | bbc | done |
| 2 | TestControlExitCorners.test_exit_while_repeat | mini | 1 |
| 3 | TestControlExitHierarchy.test_exit_for_deep | mini | 3 |
| 4 | TestNestedForMatching.test_nested_fors_correct_next_vars | bbc | four lines: 11, 12, 21, 22, each with nine leading spaces |

Use a fresh RUN per menu case. The original numbered `.bas` files are unchanged;
only the menu bundle offsets line numbers to separate cases. The exporter only
bundles independent examples without numeric branch references, DATA pooling,
external I/O, or other detected dependencies that renumbering could disrupt.
The bundle does not add a GOSUB frame around the test. See `representative_menu`
in the manifest for the exact mapping to original exported runs.

The exported `.bas` files capture the interpreter's stored program, not necessarily
its original input: Python had already normalised WEND to ENDWHILE in the `mini`
cases. These native comparisons therefore concern stored-program semantics.
The exporter now also retains `.input.bas` submissions when all program lines
were captured through `set_program_line`, and marks differences in new manifests.
These original 18 exports predate that addition. Source provenance and possible
direct host mutations must still be reviewed; mocks/state are not transplanted.

## Native results (BBCSDL 1.44a, 2026-10-20)

The user saved `representative-menu.bbc`; its SHA-256 is
`dd54f564654ff300bc47f9694d29dca6a2e2305634674201cfe66d814bf0cd57`.
All four stored-program cases completed without errors, crashes or timeouts.

| Case | Comparison with recorded Python output |
|---|---|
| 1, bbc | Exact match: done |
| 2, mini | Same value 1; SDL adds nine leading spaces |
| 3, mini | Same value 3; SDL adds nine leading spaces |
| 4, bbc | Exact match, including numeric padding |

[Raw logs and exact comparisons](../runs/python-control-flow-stored-2026-10-20/results.json)
retain the whitespace differences; the runner does not normalise them away.

```powershell
python compare/reference/run_bbcsdl_checks.py --output compare/reference/runs/new-python-check --exported-menu compare/reference/python-mini-basic-control-flow/representative-menu.bbc
```

This checks four representative stored programs, not all 18 examples or every
Python test assertion. It confirms these EXIT/stack paths, including the formerly
unclosed-IF regression, without establishing blanket dialect compatibility.

## Reproduce or select other Python tests

From the lispy3 repository root, use a new export directory:

```powershell
python compare/reference/export_python_mini_basic.py --repo C:\Users\admin\mini_basic --output compare/reference/python-mini-basic-new test/test_control_flow.py::TestExitLeavesUnclosedIfBlock test/test_control_flow.py::TestControlExitCorners test/test_control_flow.py::TestControlExitHierarchy test/test_control_flow.py::TestNestedForMatching
```

The exporter accepts other test paths/node IDs. Select bounded, non-graphics
tests first; test execution itself is real Python execution. It does not provide
a hard timeout around arbitrary Python tests. The known selected tests completed
in about three seconds. Generative exports are a reproducible sample, not all
possible examples.

A full backend replacement is a separate task. Python mocks, timing assertions,
expression-only `eval_expr` checks, interpreter-internal stack assertions, input
and filesystem fixtures cannot be transplanted by swapping `run()` alone.
Programs relying on pre-run host state also need review. Their Python assertions
remain in the source tests; the exported output does not recreate them.
Native errors/output must be recorded and compared explicitly before declaring
any exported program BBCSDL-compatible.
