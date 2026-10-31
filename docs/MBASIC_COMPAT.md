# MBASIC compatibility tests

Lispy BASIC's MBASIC print style (Eval → BASIC Settings → MBASIC, or
`(bbc-set-print-style! :mbasic)`) is checked against Microsoft BASIC-80 5.21
with the test programs of Aaron Wohl's
[MBASIC](https://github.com/avwohl/mbasic) project
([documentation](https://avwohl.github.io/mbasic/)).

## Source of the tests

The programs are in `basic/dev/tests_with_results/` of that repository: each
`test_name.bas` has a `test_name.txt` holding the output of the real
`mbasic.com` 5.21 binary under cpmemu (see the folder's README). They are
GPLv3, so they are not copied into Lispy; the test reads them from a clone.

## Setting up the clone

Clone the repository in your home folder, beside your Lispy checkout (and the
Python mini_basic project), so that it is `../mbasic` seen from Lispy:

```console
cd ~
git clone https://github.com/avwohl/mbasic.git
```

A fork works the same, for example `https://github.com/pyTony/mbasic.git`.
`tests/test_mbasic_compat.py` looks for the tests in this order:

1. the folder named by the `LISPY_MBASIC_DIR` environment variable;
2. `mbasic` inside the Lispy checkout: a clone or a link to one, ignored by
   git (`.gitignore` lists `/mbasic`). On Windows:
   `mklink /J mbasic ..\mbasic`; elsewhere `ln -s ../mbasic mbasic`;
3. `../mbasic`, beside the checkout.

Without any of them the test is skipped.

## Running

```console
python -m unittest tests.test_mbasic_compat -v
python -m pytest tests/test_mbasic_compat.py
```

## The expected table

`EXPECTED` in the test names every program: `pass` must match the real
output, and everything else is an expected failure with its reason. A program
that starts to pass fails the test until it is marked `pass`, so the table is
the current MBASIC backlog. A new program in the suite also fails until it is
added.

Lispy keeps deliberate restrictions where they are useful, even where MBASIC
allows more. For example a variable name such as `GOTO10`, which runs a keyword
into a name, is rejected. Such a program stays an expected failure with that
reason; it is not "fixed" to match MBASIC.

Results on 2026-10-25 (39 programs), and Lispy again on 2026-10-31 after
SWAP, `MID$` assignment, string comparison and INKEY$ were added:

| Runner | Pass | Spacing only | Fail |
| --- | --- | --- | --- |
| Lispy MBASIC print style (2026-10-31) | 10 | 2 | 27 |
| Lispy MBASIC print style | 5 | 2 | 32 |
| Python mini_basic `--dialect mits` | 25 | 1 | 13 |
| Python mini_basic `--dialect mini` | 7 | 3 | 29 |

Python mini_basic runs the same programs in its own optional golden ladder,
[`test/test_mbasic521_golden.py`](https://github.com/pyTony/mini_basic/blob/dev/test/test_mbasic521_golden.py)
on its `dev` branch (fetch them first with `test/manual/fetch_mbasic_golden.py`;
see [MITS_IMPLEMENTATION.md](https://github.com/pyTony/mini_basic/blob/dev/docs/MITS_IMPLEMENTATION.md)).
Its MITS dialect is the closest. Its remaining differences are
mostly single-precision numbers printed as full doubles and missing number
spaces in PRINT; those are mini_basic changes, made in that project.
