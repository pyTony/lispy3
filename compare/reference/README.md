# BBCSDL reference checks

For the user's **Python mini_basic test suite**, see
[the extracted control-flow programs](python-mini-basic-control-flow/README.md).
They are separate from the lispy3-derived jump fixture described below.

Reference installation: `C:\Program Files (x86)\BBC BASIC for SDL 2.0\bbcsdl.exe`,
file version **1.44a**, inspected and run 2026-10-20. All 14 cases completed in
isolated processes with no crashes or timeouts: 13 normal outputs and one
expected missing-target error. These observations apply to the exact cases
below, not to arbitrary jumps across control structures.

The user supplied the native tokenised program as
`C:\Users\admin\mini_basic\showcase\jumping.bbc`. An unchanged copy is kept here
as `jumping.bbc` (1842 bytes; SHA-256
`6ab9dad2802d6ef5f2c921482eeda4af8f115748946baaa0b972c6c3ead9e51c`).
BBCSDL 1.44a successfully loaded it and displayed the test menu on 2026-10-20.
Automated Enter did not submit the INPUT prompt during the initial UI attempt;
the isolated runner below bypasses that UI problem.

## Run all cases without keyboard input

```powershell
python compare/reference/run_bbcsdl_checks.py --output compare/reference/runs/new-run
```

Use a new output directory for each run. The runner checks the supplied fixture's
SHA-256 before making instrumented copies. It replaces only selection line 110
with `choice%=N`, inserts a native `*SPOOL` line, and substitutes native `*QUIT`
for terminal END tokens (including the error handler) so processes exit.
Existing test tokens and encoded jump targets remain unchanged. This is narrow
fixture instrumentation, not a source-code tokenizer. Each case gets a fresh
hidden BBCSDL process and a five-second timeout; only its own process is killed
if it hangs. Exit code zero alone does not mean success: inspect the captured
output because the error handler also exits normally.

Recorded run: [raw logs and results.json](runs/bbcsdl-1.44a-2026-10-20/results.json).
Generated instrumented `.bbc` copies are ignored by Git; the supplied original,
runner, raw text logs, and JSON results provide the reproducible record.

## Save once, run individual cases

1. Open the supplied `jumping.bbc` directly in the BBCSDL editor. No conversion
   is needed. Alternatively, open `bbcsdl-jumps.bas` as text.
2. If starting from text, save in BBCSDL's native tokenised format as a `.bbc` file.
3. Run it and enter a test number from 1 to 14.
4. Record the output or error, including the reported line number. If it hangs,
   interrupt it and record that outcome.
5. Use a fresh **RUN** for each case. Do not continue after an error or jump
   directly into another case: this avoids carrying abandoned stack entries
   between tests.

This is one program to save manually; no tokenizer has been added. The menu
enters each case with `GOTO`, avoiding a `GOSUB` return frame around the test.
An error handler reports `ERR`, `ERL`, and `REPORT`, then ends execution.

## Recorded results (2026-10-20)

The output column lists the current lispy3 test expectation, with `/` separating
lines. It is a comparison aid, not an assertion about valid BBCSDL usage.

| Case | Behavior | Current expected output | BBCSDL 1.44a observation |
|---|---|---|---|
| 1 | GOTO within FOR; reach NEXT | 1 / 2 / 3 / done | Matches |
| 2 | GOTO within WHILE; reach ENDWHILE | 1 / 2 / done | Matches |
| 3 | GOTO within multi-line IF | inside / after | Matches |
| 4 | GOTO from IF to enclosing active FOR | 1 / 2 / done | Matches |
| 5 | GOTO out of FOR and IF | out | Matches; exit-only, not stack-cleanup evidence |
| 6 | Backward GOTO within WHILE | 3 | Matches |
| 7 | GOTO within ELSE | else / after | Matches |
| 8 | ON GOTO within REPEAT | 1 / 2 | Matches |
| 9 | GOTO within CASE | case / after | Matches, including numbered WHEN |
| 10 | GOTO nonexistent line 999 | Error identifying missing target | ERR 41 at line 10020: No such line |
| 11 | GOSUB returns to next same-line statement | sub / back | Matches |
| 12 | Nested GOSUB returns | outer / inner / outer back / main | Matches |
| 13 | GOSUB within FOR | 1 / 2 / done | Matches |
| 14 | ON GOSUB selects second target | second / back | Matches |

Cases correspond to `NestedJumpRegressionTest` and `SubroutineAcceptanceTest`
in `tests/test_mini_basic_tdd.py`. Numeric line labels and jump destinations
are offset to keep cases separate. Case 9 uses numeric labels instead of the
test's symbolic label; it also probes the numbered-WHEN syntax that lispy3's
reader currently rejects.

## Documented restrictions versus observations

The [shared BBCSDL/BB4W manual, Program structure limitations](https://www.bbcbasic.co.uk/bbcwin/manual/bbcwin2.html)
explains that leaving FOR, REPEAT, or GOSUB without its corresponding terminator
can leave entries on the shared stack. A later ENDWHILE or UNTIL may then fail.
It recommends structured exits such as EXIT or returning from a procedure.

Case 5 terminates immediately after printing `out`, so it does not exercise that
later failure. lispy3 unwinds its host-language body when jumping out; matching
this case's output does not establish identical stack behavior. The additional
probes below confirm the reference error. Decide explicitly whether to reproduce
BBCSDL's errors or document an intentional extension before changing lispy3's
continuation semantics. Symbolic-label behavior is also not verified by case 9's
numeric-label variant. Cases 11-14 confirm reference behavior only: lispy3's
subroutine acceptance tests still fail because those features are unimplemented.

## Small loops after exit: recorded 2026-10-20

Three instrumented variants of case 5 ran on BBCSDL 1.44a in fresh hidden
processes, with no crashes or timeouts. Each copies existing tokenised loop
records from the supplied fixture; the original file remains unchanged.

| Probe | After jumping out of the inner FOR | BBCSDL result | Evidence |
|---|---|---|---|
| `fresh-for` | Start and complete a new FOR loop | out / 1 / 2 / 3 | [Log](runs/exit-fresh-for-2026-10-20/case-05.txt) |
| `fresh-while` | Start and complete a new WHILE loop | out / 1 / 2 | [Log](runs/exit-fresh-while-2026-10-20/case-05.txt) |
| `enclosing-while` | Reach ENDWHILE of a loop entered before the FOR | out / ERROR 46 AT LINE 5082 / Not in a WHILE loop | [Log](runs/exit-enclosing-while-2026-10-20/case-05.txt) |

The last probe's case body is equivalent to:

```basic
5005 n=0
5006 WHILE n<2
5010 FOR i=1 TO 2
5020 IF TRUE THEN
5030 GOTO 5080
5040 ENDIF
5050 PRINT "wrong"
5060 NEXT
5080 PRINT "out"
5081 n+=1
5082 ENDWHILE
5090 END
```

For `fresh-for`, the original case has `FOR i=1 TO 3`, `PRINT ;i`, `NEXT`
inserted after line 5080. For `fresh-while`, it has `n=0`, `WHILE n<2`,
`n+=1`, `PRINT ;n`, `ENDWHILE` inserted there. A fresh loop succeeding does
not establish that an earlier abandoned frame was removed.

Reproduce a probe with a new output directory:

```powershell
python compare/reference/run_bbcsdl_checks.py --output compare/reference/runs/new-probe --exit-probe enclosing-while
```

If reusable tokenising support becomes necessary, implement it in mini-basic
rather than creating a separate tokenizer solely for this reference runner.

## Reaching a terminator without its opening statement

Recorded on BBCSDL 1.44a, 2026-10-20. Six isolated probes initialise `n=0`,
then jump past the opening statements to `PRINT "out"` at line 5080. Line 5081
contains the terminator being tested; line 5082 prints `after` if execution
continues. All six processes completed without a crash or timeout.

| Terminator at 5081 | Observed result after `out` |
|---|---|
| NEXT | ERR 32: Not in a FOR loop |
| UNTIL n=2 | ERR 43: Not in a REPEAT loop |
| ENDWHILE | ERR 46: Not in a WHILE loop |
| ENDIF | Prints after; no error |
| ENDCASE | Prints after; no error |
| RETURN | ERR 38: Not in a subroutine |

All reported errors identify line 5081.
[Raw results and individual logs](runs/orphan-terminators-2026-10-20/results.json)
are retained. Reproduce with:

```powershell
python compare/reference/run_bbcsdl_checks.py --output compare/reference/runs/new-terminator-check --terminator-probe all
```

These are observations about the precise probes, not a recommendation to jump
into inactive bodies or a requirement to weaken lispy3's structural validation.
The earlier procedure-return and LOCAL-restoration tests in
`tests/test_mini_basic.py` have not yet been reproduced on BBCSDL by this runner;
neither have ENDPROC-without-PROC or RETURN-with-abandoned-inner-loop cases.

## Preferred loop exits

Use the shared manual's structured-exit guidance as the baseline. Complete a
loop through its own NEXT, UNTIL, or ENDWHILE after setting the loop variable or
condition to end it, or use the applicable EXIT statement. A jump to NEXT can
work when the active FOR's variable has been set to its limit; a jump to
ENDWHILE alone does not force an exit if the condition is still true. Jumping
to a terminator without the matching active opening statement is a different
case, as demonstrated above.

Treat cross-boundary jumps as compatibility/diagnostic probes, not encouraged
programming patterns. Prioritise tests of normal termination, adjusted loop
values/conditions, and structured EXIT, then document any deliberate differences
in error detection or stack cleanup. The runner has not yet checked every
earlier lispy3 stack/exit test against BBCSDL.
