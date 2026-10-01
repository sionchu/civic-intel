# Cost-aware execution routing

Optimize for a verified milestone with bounded tasks, rather than repeated whole-repository reads.
MAIN owns architecture decisions, shared contracts, integration and final verification.

| Work | Runtime routing | Limit |
|---|---|---|
| Read-only inventory, reference maps, bounded docs/CI transformations | `gpt-6-luna`, low reasoning when explicitly selectable | One focused task; no child delegation |
| Behavior-preserving extraction or nontrivial local implementation | `gpt-6.1-sol`, medium reasoning when explicitly selectable | One owned vertical slice/worktree |
| Ambiguous identity/evidence semantics, transaction boundary, final cutover judgment | MAIN with its configured model; raise reasoning only if supported | Resolve one decision, then return to bounded execution |

The current collaboration API exposes `model` and `reasoning_effort` for a fresh or limited-history
child. A full-history fork inherits MAIN's settings; do not claim a cheaper override on that fork.
Existing agents retain their assigned model when followed up. Tool availability controls execution;
a role file or a model name in this document is not evidence of isolation, authorization or pricing.

Do not invent configuration fields, install another bridge, or launch nested Codex processes to
simulate routing. If selection is unavailable, use the configured model with narrower inputs and
deterministic scripts. One MAIN and at most three concurrent children, no recursive fan-out.
Read-only independent reviewers remain independent of production edits. External review requires
the applicable privacy/authorization boundary and never substitutes for executed verification.
