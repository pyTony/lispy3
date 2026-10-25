# Libraries and selective imports

Use `load` to run an existing Lisp script in the shared workspace. Use `import`
when a library declares public exports and keeps its helpers private. The forms
below are lispy3's Scheme-inspired subset, not a complete Scheme library standard.

Use `(load "path/to/library.lisp" :silent)` to suppress the loader's status
message. Explicit program output and errors remain visible. Lispy Machine also
provides **File → Load library silently…**. Imports already produce no status
message.

## Import just what you need

```lisp
(import (only mini-basic CLS COLOUR ANSI ANSI-RESET))
(CLS)
(COLOUR 1)
(ANSI 27 "[0m")
```

Or give commands a prefix to avoid names already used in your workspace:

```lisp
(import (prefix (only mini-basic CLS COLOUR ANSI ANSI-RESET) term:))
(term:CLS)
(term:ANSI 27 "[32m")
(term:ANSI-RESET)
```

In a fresh workspace, select/rename individual exports:

```lisp
(import (rename (only mini-basic CLS) (CLS clear-screen)))
(clear-screen)
```

| Form | Effect |
|------|--------|
| `(import library)` | Import all declared exports |
| `(import (only library a b))` | Import just a and b |
| `(import (prefix library lib:))` | Import exports as lib:name |
| `(import (rename library (old new)))` | Rename selected exports; retain the rest |
| `(import set1 set2)` | Import multiple sets, checking collisions together |
| `(import "path/to/library.sld")` | Load a named library declaration from that file |

Modifiers compose: `(prefix (rename (only library f) (f calculate)) lib:)`
imports f as lib:calculate. Symbols and lists of symbols can name a library;
`(example maths)` is looked up as `lisp/example/maths.sld`.

A missing export or a name already bound in the destination raises an error.
Use a prefix or rename to resolve it. A repeated identical import is allowed
and does not run initialization again. Imported variable bindings are live but
read-only: private library code can change its own state, while callers cannot
`set!` or redefine an imported name. This does not freeze exported mutable values.

Imports and library declarations are top-level syntax. Like macro definitions,
they take effect during expansion; source loaded into one begin can import names
and use their macros in later forms. They are not conditional runtime operations.

## Define a library

Save this as `lisp/example/counter.sld` (create the directory first):

```lisp
(define-library (example counter)
  (export next count)
  (begin
    (define count 0)
    (define (next)
      (set! count (+ count 1))
      count)))
```

Then:

```lisp
(import (prefix (example counter) counter:))
(counter:next)  ; 1
counter:count   ; 1, a live exported binding
```

Supported declarations are `(export ...)`, `(import ...)`, `(begin ...)` and
`(include "source.lisp" ...)`. Export `(rename internal external)` to give an
internal name a different public name. Declarations are processed in order;
exports are checked after initialization. A library file contains exactly one
`define-library` form. Includes and string-path dependencies resolve relative to
the declaring file; ordinary named dependencies are found under `lisp/`.

Each library has its own environment and macro table, initialized with standard
primitives. Caller workspace definitions are not implicit dependencies. Libraries
must explicitly import dependencies. Loaded declarations are cached for the
interpreter session; two different files cannot silently claim the same name.
Cyclic file imports report an error. Failed initialization does not publish a
half-built library. Loading a library runs its initialization code, so it is
not a security sandbox.

## Macros keep their helpers

```lisp
(define-library example-macro
  (export add-ten)
  (begin
    (define (helper x) (+ x 10))
    (define-macro (add-ten x) `(helper ,x))))
(import (only example-macro add-ten))
(let [value 5] (add-ten value))  ; 15
```

The helper stays private and resolves in the library even if the caller has a
function named helper. The argument value resolves in the caller. Private
macros can support public macros without being imported themselves.

This supports lispy3's procedural `define-macro`, not full hygienic `syntax-rules`.
Use `gensym` for introduced temporary variables to avoid capturing caller names.
Macros that deliberately construct symbols from text do not acquire automatic
use-site scope. Expanded internal binding references are interpreter objects,
not portable Lisp source. Keep original source containing import forms.

## mini-basic and compatibility

`lisp/mini-basic.sld` declares its public reader, statement, data, array, terminal
and comparison interfaces. Importing CLS retains its runtime helpers privately;
it does not populate the workspace with bbc-cls or the parser. Reader macros
such as bbc-run work through their private parser and statement macros too.
See the [mini-basic guide](MINI_BASIC.md) for language and terminal limits.

Existing `(load "mini-basic")` still installs definitions in the shared
workspace. Do not expect load and an unprefixed import of the same names to
combine without collisions; use a fresh workspace or prefix imports.

Workspace `(save ...)` rejects imported bindings before writing a file because
closures and private macro bindings are not yet serializable. Save your original
source with its imports instead. Reload/unload, library version declarations,
syntax-rules and portable serialization remain future work. Both the normal
interpreter and the optional NumPy evaluator support the import forms.

## Plain file modules and lifecycle

A string import naming a plain `.lisp` file now creates a private module without
requiring a define-library wrapper. Its actual definitions/macros are exported;
standard builtins and imported dependencies are not automatically exported.
Existing only/prefix/rename modifiers apply. `load` remains the legacy shared
script operation.

Use `(unload "file.lisp")` or `(reload "file.lisp")` for explicit module
lifecycle; named declarations can use `(unload 'name)`. Reload refreshes recorded
imports, keeping aliases and selections, and drops removed exports. Live library
dependents must be unloaded first. Register managed cleanup with
`(module-on-unload cleanup)` inside the module. See [WORKSPACES.md](WORKSPACES.md)
for atomic binding replacement, side-effect limits and cleanup behavior.
