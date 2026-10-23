"""Object-preserving workspace switches for a single lispy3 runtime.

Integration (owned by the runtime caller): after library_system initialization,
construct WorkspaceManager(sys.modules[__name__]). Construction adopts the exact
existing global_env, macro_table and library_system objects. Expose any Lisp
wrappers with add_initializer(callback), where callback receives env, and install those
wrappers in the adopted current workspace explicitly as well. Register future
extension bindings in manager.workspace_initializers; never seed fresh workspaces
by copying the live environment. Initializers run with their workspace active.

Call evaluators/completion with the current environment explicitly: this module
does not repair Python default arguments captured by existing runtime functions.
All switches rebind runtime globals; they are synchronous and require serialized
runtime access. This is state isolation, not a security or process boundary.
Public API: new(name=None) (also new_workspace) resets current state while
preserving the saved stack; push(name=None) saves current and activates fresh;
pop() cleans current and restores the last saved workspace. depth counts saved
workspaces. Names are optional labels, not lookup keys. current/capture return
the exact Workspace. use(workspace) temporarily borrows it without cleanup.
add_initializer(callback) registers callback(env) for future fresh creation;
workspace_initializers remains the lower-level list of callback(workspace).
on_discard(callback) registers cleanup on current state. Cleanup is LIFO, once,
and rejects new/push/pop/use/discard reentrancy. All callbacks are attempted;
new/pop finish switching before propagating the first cleanup exception.

Parent installs new-workspace/workspace-push/workspace-pop as special forms,
not ordinary procedures. workspace-on-discard may call manager.on_discard with
a zero-argument Lisp Procedure or Python callable. Cleanup runs while departing
state is installed, before replacement, and never clears its dictionaries.
Managed resources may register zero-argument cleanup callbacks with on_discard;
discard cannot undo file writes, graphics, imports or other external side effects.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field

from lispy_support.lispy_libraries import LibrarySystem


@dataclass(eq=False)
class Workspace:
    """One environment and its associated macro and library state."""

    env: object
    macro_table: dict
    library_system: LibrarySystem
    _owner: object = field(repr=False)
    name: object = None
    _cleanups: list = field(default_factory=list, repr=False)
    _discarded: bool = field(default=False, repr=False)

    def add_cleanup(self, callback):
        """Register a zero-argument managed-resource release, run on discard."""
        if self._discarded:
            raise ValueError('workspace has been discarded')
        if not callable(callback):
            raise TypeError('cleanup must be callable')
        self._cleanups.append(callback)


class WorkspaceManager:
    """Adopt runtime state, create fresh workspaces, and switch by reference."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.workspace_initializers = []
        self._current = Workspace(runtime.global_env, runtime.macro_table,
                                  runtime.library_system, self)
        self._stack = []
        self._borrowed = []
        self._cleaning = False

    @property
    def current(self):
        return self._current

    @property
    def depth(self):
        """Number of workspaces saved by push in the current context."""
        return len(self._stack)

    def _check_transition(self):
        if self._cleaning:
            raise RuntimeError('workspace transitions are forbidden during cleanup')

    def capture(self):
        """Return the current workspace itself, without copying any state."""
        return self._current

    def _validate(self, workspace):
        if not isinstance(workspace, Workspace) or workspace._owner is not self:
            raise ValueError('workspace belongs to another manager')
        if workspace._discarded:
            raise ValueError('workspace has been discarded')

    def _activate(self, workspace):
        self.runtime.global_env = workspace.env
        self.runtime.macro_table = workspace.macro_table
        self.runtime.library_system = workspace.library_system
        self._current = workspace

    def add_initializer(self, callback):
        """Run callback(env) on each future fresh workspace while it is installed."""
        if not callable(callback):
            raise TypeError('initializer must be callable')
        self.workspace_initializers.append(lambda workspace: callback(workspace.env))

    def on_discard(self, callback):
        """Register zero-argument cleanup for current state (including Lisp procs)."""
        self.current.add_cleanup(callback)

    def _create(self, name=None):
        """Build fresh state without discarding the caller."""
        workspace = Workspace(self.runtime.standard_env(), {},
                              LibrarySystem(self.runtime), self, name)
        try:
            with self.use(workspace):
                for initialize in tuple(self.workspace_initializers):
                    initialize(workspace)
        except BaseException:
            self.discard(workspace)
            raise
        return workspace

    def new_workspace(self, name=None):
        """Replace current state, running its cleanup once before switching.

        Build and initialize first, so initializer failure preserves old state.
        A cleanup failure still completes the switch and is then propagated.
        """
        self._check_transition()
        if self.current in self._borrowed or self.current in self._stack:
            raise ValueError('cannot discard a saved workspace')
        workspace = self._create(name)
        try:
            self._cleanup(self.current)
        finally:
            self._activate(workspace)
        return workspace

    def create(self, name=None):
        """Create independent inactive state without replacing or saving current."""
        self._check_transition()
        return self._create(name)

    def new(self, name=None):
        """Activate fresh state and discard current; preserve the saved stack."""
        return self.new_workspace(name)

    def push(self, name=None):
        """Save current state and activate a fresh workspace; do not clean up."""
        self._check_transition()
        workspace = self._create(name)
        self._stack.append(self.current)
        self._activate(workspace)
        return workspace

    def pop(self):
        """Restore saved state and discard the departed workspace.

        An empty stack raises IndexError without changing anything. Restoration
        completes even when a cleanup callback raises; cleanup sees old state.
        """
        self._check_transition()
        if not self._stack:
            raise IndexError('no saved workspace')
        departed = self.current
        previous = self._stack.pop()
        try:
            self._cleanup(departed)
        finally:
            self._activate(previous)
        return self.current

    @contextmanager
    def use(self, workspace):
        """Temporarily borrow workspace; restore on exit without discarding it.

        Push/pop inside a use block have their own stack, so pop cannot consume
        the caller's saved state. Callers must pop their temporary workspaces
        before leaving the block, or retain and explicitly discard them later.
        """
        self._check_transition()
        self._validate(workspace)
        previous, stack = self.current, self._stack
        borrowed_count = len(self._borrowed)
        self._borrowed.extend([previous, *stack])
        self._stack = []
        self._activate(workspace)
        try:
            yield workspace
        finally:
            self._activate(previous)
            self._stack = stack
            del self._borrowed[borrowed_count:]

    def discard(self, workspace):
        """Release inactive state once, in reverse registration order.

        All callbacks are attempted; the first failure is then raised. Active,
        stacked and context-saved workspaces cannot be discarded.
        """
        self._check_transition()
        if not isinstance(workspace, Workspace) or workspace._owner is not self:
            raise ValueError('workspace belongs to another manager')
        if workspace._discarded:
            return
        if (workspace is self.current or workspace in self._stack or
                workspace in self._borrowed):
            raise ValueError('cannot discard an active or saved workspace')
        with self.use(workspace):
            self._cleanup(workspace)

    def _cleanup(self, workspace):
        if workspace._discarded:
            return
        workspace._discarded = True
        callbacks, workspace._cleanups = workspace._cleanups, []
        error = None
        self._cleaning = True
        try:
            for callback in reversed(callbacks):
                try:
                    callback()
                except BaseException as exc:
                    if error is None:
                        error = exc
        finally:
            self._cleaning = False
        if error is not None:
            raise error
