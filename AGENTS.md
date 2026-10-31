# Shared agent coordination

Before editing, read [docs/AGENT_COORDINATION.md](docs/AGENT_COORDINATION.md).
This applies to Codex, Claude and other assistants equally.

- Branch from `dev` and open PRs into `dev`. `main` is the pruned release tree
  and is updated only with `python tools/release_main.py`; never merge `main`
  into `dev`. See [repository layout](docs/REPOSITORY_LAYOUT.md#branches).
- Inspect open PRs, their coordination blocks, and local worktree status first.
- An open PR reserves its declared scope until merged, closed or explicitly
  handed off. Draft means unfinished; ready for review does not mean unowned.
- Publish your owner, branch, scope, state and next action in the PR description.
  Create a draft PR early, before substantial implementation.
- Use a separate worktree for concurrent work. Never switch, reset, stage or
  commit another agent's checkout or the user's unrelated changes.
- Do not edit another owner's reserved scope without an explicit handoff.
  Read-only review and independent tests are allowed.
- Recheck remote state before starting edits and before pushing. Update the PR
  coordination block when pausing, changing scope or finishing implementation.
- Do not infer abandonment from age or silence. Ask for a handoff when needed.

These are cooperative locks, not enforcement by GitHub. See the protocol for
overlapping files, shared documentation and crash recovery.

## Keep the feature matrix current

Development goes in small steps, and the docs move with each step.
Every PR that adds, removes or changes a user-visible feature also, in the
same PR:

- updates its row in [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md) and the
  page's "Last checked" line;
- adds a CHANGELOG "Unreleased" entry, and for a Lisp built-in its
  `HELP_TOPICS` entry and docs/QUICK_REFERENCE.md line.

`tests/test_feature_matrix.py` checks that every built-in topic, every docs
page and the MBASIC golden counts appear in the matrix, so a missed update
fails the tests.
