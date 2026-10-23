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
