# Workspaces, program runs and file modules

A workspace owns its variables, functions, memo caches, macros and library/module
registry. Fresh workspaces are built from the interpreter's base environment,
including installed NumPy/editor primitives. They do not copy the old workspace.
Lisp function parameters, `let` and loop bindings keep their normal lexical scope.
BASIC variables keep their existing program-wide visibility within an execution.

## Run versus Eval

| Action | State |
|---|---|
| F6: Run program → Listener | Fresh workspace for the whole Lisp/BASIC buffer |
| Shift+F6: Run program → ANSI terminal | Same fresh-run rule, real terminal output |
| F5 / Ctrl+Enter | Evaluate form/selection in the current workspace |
| Ctrl+Shift+Enter | Evaluate whole buffer in current workspace |
| Ctrl+F6: Run tests in buffer | Fresh workspace, buffer run silently, then `(run-tests)` |
| F9 / Listener input | Evaluate in current workspace |
| F7/F8 Python mini_basic, or Python buffers | Existing fresh subprocess behavior |

After a program run, its definitions remain available for inspection and
interactive Eval. The next Run starts fresh, so an old BASIC loop counter cannot
supply an uninitialised variable in another program. The current BASIC reader's
unbound-variable errors remain unchanged; isolation does not introduce default
values or change the dialect's loop scope. Syntax/read errors detected before a
run do not discard the old workspace. Runtime failures leave the new workspace's
partial state available for inspection. Only one evaluation runs at a time.

The status bar identifies the current workspace and saved stack depth.
Workspace → New / Push / Pop changes execution state, keeping every editor
buffer and unsaved edit open. It does not rerun startup.lisp implicitly.

## Preserve and restore state in memory

```lisp
(define answer 42)
(workspace-push "experiment")
;; A fresh environment: answer is not defined here.
(define answer 99)
(workspace-pop)
answer                         ; 42
```

`(new-workspace)` replaces only the current workspace. An optional string labels
it, for example `(new-workspace "search demo")`. A saved push/pop stack survives
New. `(workspace-name)` and `(workspace-depth)` report the active label and count.
Pop on an empty stack reports an error and changes nothing.

Push retains the exact old environment, closures, mutable objects, macro table,
module instances and memo caches. Pop discards the temporary workspace and
restores those objects. These are memory operations, not disk snapshots.
Transitions must be standalone top-level commands: they cannot occur inside a
running function, `begin`, module body, dynamic `eval` or cleanup callback.

## Import names explicitly; keep file state private

Legacy `(load "file" :silent)` still evaluates a script into the shared current
workspace. Its definitions are not attributed to an unloadable module. Use an
explicit import for file-local state:

```lisp
(import (prefix "search.lisp" search:))
(search:find-item items target)
```

A plain `.lisp` file becomes a cached module with its own environment. Its actual
definitions and macros are exported; dependencies and preinstalled builtins are
not automatically re-exported. A `.sld` / `define-library` declaration retains its
existing explicit export list, which is preferable for a deliberately small API.
Relative imports inside modules resolve from that module's directory.

| Python analogy | lispy3 |
|---|---|
| `import lib` | `(import (prefix "lib.lisp" lib:))`, then `(lib:f ...)` |
| `from lib import f` | `(import (only "lib.lisp" f))` |
| `from lib import *` | `(import "lib.lisp")` |

This is an analogy, not identical reload behavior. Lispy3's existing imported
bindings are live library references; reload refreshes its recorded imports.
Imports reject collisions instead of silently replacing unrelated names.

```lisp
(reload "search.lisp")          ; fresh state, reread the file
(unload "search.lisp")          ; detach tracked imports and release resources
```

Workspace → Reload module… / Unload module… offers the same operations.
Named libraries can use a quoted name, e.g. `(unload 'sample)`.
Reload keeps prefixes, `only` and renamed selections, removes deleted exports,
and gives wildcard imports new exports. A failed staged reload retains the old
instance and bindings. External effects already performed by the failed attempt
are not rolled back. Unload/reload refuses a module that other loaded modules
still import; unload the dependents first. Inline libraries without a source
file can be unloaded but cannot be reloaded.

Copied function/value references are not revoked by unload. They may keep old
objects alive. Unload removes only bindings the module still owns; it is not a
heap purge or undo of arbitrary shared mutation.

## Side effects and managed cleanup

Loading a module can have effects, and reload can repeat them. Prefer definitions
at load time and explicit start/stop functions. Register resource release when
needed:

```lisp
(workspace-on-discard (lambda () (display "workspace released")))
;; Inside an imported file/library:
(module-on-unload (lambda () (display "module released")))
```

Callbacks take no arguments, run once in reverse registration order under their
old environment, and can close the windows, timers, ports or connections the
program explicitly manages. Module dependents are cleaned before dependencies.
Push does not clean or suspend old resources. Pop/New cleans the departing
workspace; unload/reload cleans the old module instance. All callbacks are
attempted if one fails. Cleanup errors are reported; a completed New/Pop or
committed module replacement remains in effect. Recursive lifecycle changes
and new imports during cleanup are rejected.

No operation undoes terminal output, file writes, network requests, host objects
or unmanaged process-global graphics/timers. In particular, Python turtle and
other host graphics backends do not acquire private screens automatically.
Register appropriate cleanup for resources your code owns. Workspaces isolate
Lisp state; they are not processes, security sandboxes or suspension of external
activity. Disk workspace serialization and automatic dependency reload are not
implemented.

## Practice in other Lisps

[Racket's module guide](https://docs.racket-lang.org/guide/module-basics.html)
usually associates a module with a file, exposes selected definitions through
`provide`, and keeps other names private. [Its namespaces](https://docs.racket-lang.org/guide/mk-namespace.html)
separate evaluation environments and module registries.
[Clojure namespaces](https://clojure.org/reference/namespaces) provide named
mappings, aliases, explicit references and removal through `ns-unmap`/`remove-ns`.
[Common Lisp LOAD](https://www.lispworks.com/documentation/HyperSpec/Body/f_load.htm)
executes file forms into the Lisp environment; a file is not automatically a
private module. Lispy3 combines explicit Scheme-style imports with an explicit
workspace lifecycle, rather than treating every legacy load as isolated.
