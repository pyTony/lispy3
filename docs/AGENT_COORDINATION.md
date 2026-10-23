# Coordination between assistants

Open pull requests are the shared work register. Each unfinished PR must say
who owns the work, what is being edited, its current state and what happens
next. Local chat history is not a shared work register.

## Claim work before implementation

1. Inspect all open PRs, including drafts, their changed files and descriptions.
   Inspect `git status` and `git worktree list` locally. Read existing changes
   without modifying them. An existing branch name alone is not authorization
   to use that checkout.
2. Choose an unclaimed scope and a separate branch/worktree. Reserve files by
   default. For a large shared file, reserve a named function/class or section
   only when both owners explicitly agree on that division.
3. Create a draft PR with the coordination block below before substantial
   implementation. GitHub requires a commit: a small plan or failing regression
   test is a suitable initial commit. For investigation before the first
   commit, use a draft issue with the same block, then link it from the PR.
4. Re-read open reservations after publishing yours. If claims raced, stop
   overlapping edits and agree on one owner; timestamps alone do not authorize
   overwriting either agent's changes.

```markdown
## Agent coordination

- Owner: Codex or Claude, plus a task/session identifier
- State: active | paused | blocked | awaiting-review
- Branch/worktree: branch name; local checkout path if relevant
- Reserved scope: files, directories, or mutually agreed named sections
- Current work: concrete implementation or investigation in progress
- Next action: next implementation/check, required input, or user review
- Dependencies/handoff: related PRs; explicit handoff if any
- Updated: ISO date and time with timezone
```

Keep this block in the description, so readers need not reconstruct ownership
from comments. The rest of the PR describes final behavior and validation.
Update the block at meaningful checkpoints, before pausing and before handing
control back to the user. Mark a finished implementation `awaiting-review` and
make the PR ready for review. Do not label it `active` merely because it is open.

## Lock meaning and concurrent edits

A reservation is a cooperative write lock, not a GitHub-enforced lock. Other
agents may inspect, review and run independent tests, but must not change,
commit, rebase or push the owner's branch. Use isolated worktrees for tests
that generate artifacts. Never run two writers in one checkout, including
branch switches or changes to its index.

An open PR retains its reservation while paused, blocked or awaiting review.
For overlapping work, request an explicit handoff or ask the owner to narrow
its scope in the PR. Record the new owner and scope before continuing.
The user can explicitly authorize a takeover. Silence, an old timestamp or a
missing local process is not a handoff. Stale reservations require a status
check, not automatic deletion.

Shared files such as TODO.md and README.md still count as overlapping scope.
Owners can agree to separate named sections; otherwise defer the shared-file
edit or supply it for the current owner to include. A new task must account
for existing PR changes even when implementing a different feature.

Immediately before editing and pushing, recheck PR state, scope and the local
diff. Stage explicit files or hunks. Preserve unrelated user changes. If
unexpected edits appear, stop writes to that scope and identify ownership.
Never resolve a conflict by silently dropping the other agent's work.

## Completion and recovery

After a merge, close or recorded handoff, the reservation is released. Refresh
the base branch before beginning new work. Closing an unmerged PR should say
where any unfinished implementation went. A crash leaves the reservation in
place; the returning owner updates its state, or the user assigns a takeover.

Existing PRs without a block are still reserved: inspect their descriptions
and diffs and establish ownership before overlapping work. Each owner should
backfill its own PRs. Do not guess another assistant's current activity.

## Initial register (2026-10-23)

This is a discovery aid; live PR state and coordination blocks take precedence.

| PR | Scope | Known state |
| --- | --- | --- |
| #68 | pytest discovery/configuration | Codex, awaiting review |
| #69 | GUI-thread Tk/turtle garbage collection | Codex, awaiting review |
| #71 | BASIC PRINT/VDU and parameter/LOCAL error restoration | Draft; establish owner before overlapping edits |
| #72 | BASIC Listener, file shortcuts, startup and browsing; this protocol | Codex, awaiting review |
| #73 | BBCSDL structured-control fixtures, runner and compatibility notes | Codex, awaiting review |

PRs #72 and #73 both update documentation. Their existing non-overlapping
sections are reserved separately; recheck and reconcile the final merge diff.
The user's local primes example and Mandelbrot benchmark are not owned by
these agent tasks.
