# Repository layout

The project root keeps user-facing entry points and project metadata:

- `lispy3.py`: interpreter and CLI.
- `lispy3-numpy.py`: optional NumPy evaluator and numeric operations.
- `lispy_machine.pyw`: editor launcher.
- `startup.lisp`: user-facing startup configuration, kept beside the launchers.
- `README.md`, `TODO.md`, `CHANGELOG.md`, agent instructions and pytest configuration.

Implementation helpers are in `lispy_support/`, a Python package. This includes
terminal transport, graphics, syntax colouring, workspaces, library loading,
editor utilities and the BASIC adapters. Internal Python imports use this package;
external code importing the old top-level helper names must update its imports.
No duplicate compatibility wrapper files are left at the root.

Lisp libraries stay in `lisp/`; runnable examples stay in `lisp/programs/`.
BASIC examples, benchmarks and native-reference material stay in `basic/`.
Docs, syntax rules and icons stay in `docs/`, `syntax/` and `icons/`.
These asset paths resolve from the project root, not the helper package folder.

## Commands

The existing launch commands are unchanged:

```text
python lispy3.py
python lispy3-numpy.py
python lispy_machine.pyw
python -m pytest tests
```

Standalone BASIC and utility commands now use:

```text
python -m lispy_support.basic_repl
python tools/make_shortcut.py
python tools/run_complex_checks.py
```

The BASIC REPL defaults to the project's `basic/` directory. The editor's Lisp
file browser still defaults to `lisp/programs/`, or its saved directory preference.
The ANSI viewer can still be launched by its absolute file path from another
working directory, as required by external terminal windows.

This reorganization leaves personal programs and unrelated local modifications
untouched. Settings files and startup behavior are unchanged.

## Branches

`dev` holds the whole project and is where work happens: branch from `dev`
and open pull requests into `dev`.

`main` is the release tree for people who use Lispy without developing it. It
has the same files as `dev` minus the developer-only ones listed in `DEV_ONLY`
in `tools/release_main.py`: agent instructions, `TODO.md`, `pytest.ini`,
`tests/`, `.github/`, `basic/reference/`, the developer docs and the release
tools themselves. Its README and manual pages do not link to those files.

To update `main` from `dev`:

```text
python tools/release_main.py --push
```

then open a pull request from the `release/<date>` branch it prints into
`main`. The script merges `origin/dev` into a branch made from `origin/main`
and removes the developer-only paths, which also settles the expected
"deleted in main, modified in dev" conflicts. Any other conflict (usually the
README) stops it with a list of files to fix and commit by hand. It warns
about Markdown links that would point at a removed file.

Never merge `main` into `dev`: that would delete the developer files from
`dev`. If a fix is made directly on `main`, bring it to `dev` with
`git cherry-pick`. When you add a developer-only file or folder on `dev`, add
it to `DEV_ONLY`; `tests/test_repository_layout.py` checks the list.
