# Shared agent coordination

Before editing, read [docs/AGENT_COORDINATION.md](docs/AGENT_COORDINATION.md).
This applies to Codex, Claude and other assistants equally.

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
