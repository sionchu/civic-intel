# Native admin agent execution prerequisite

Status: BLOCKED. Request preparation is delivered by
[the completed playbook slice](../completed/admin-work-playbook.md); it is not task dispatch.

## Current evidence — 2026-09-24

Civic Intel now declares every expected custom role in project `.codex/config.toml` with
`agents.<name>.description` and `agents.<name>.config_file`. Each referenced standalone file in
`.codex/agents/` is a role-specific config layer containing sandbox settings and
`developer_instructions`; role names/descriptions remain in the parent declaration.
The playbook fails closed when a declared role/layer is missing or malformed.

A `codex exec --strict-config` synthetic read-only run accepted this project configuration.
The host currently reports Codex CLI `0.156.1`; an earlier project audit observed `0.154.0`.
This checkpoint records the versions actually observed and does not infer how the installed
version changed.

In non-interactive `codex exec`, the visible native `spawn_agent` schema exposes exactly
`fork_turns`, `message`, `model`, `reasoning_effort`, and `task_name`. It exposes no
`agent_type` selector. Enabling the installed `multi_agent_v2` feature for one synthetic run
did not change that schema.
A synthetic request explicitly asking for the configured `record_curator` type returned BLOCKED
and reported zero child agents. A separate explicit GPT-5.5 coordinator control also returned
BLOCKED with zero children; changing only the coordinator model did not expose a role selector on
this installed runtime. No role-only child handoff was produced. This is the relevant negative
result; task naming is not accepted as evidence that a configured role layer loaded.

The interactive CLI path described by OpenAI could not be tested through the current remote
command channel because its stdin is not a TTY. Wrapping it with the installed Git `winpty`
still returned a non-TTY condition. That is a limitation of this remote execution channel,
not proof that interactive Codex cannot load custom agents.

Current OpenAI/upstream references used for this checkpoint:
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://github.com/openai/codex/issues/31893
- https://github.com/openai/codex/issues/31814

The documentation describes custom Codex agents and also states that subagents inherit the
parent permission mode and configured tools unless specifically overridden. Therefore a role
name or read-only shell label is not sufficient proof of MCP, account, remote-desktop or
operational-database isolation.

## Smallest unblocking proof

Use an actual interactive local Codex session, or a future non-interactive interface that exposes
configured role selection, with synthetic inputs and no operational credentials. Spawn exactly
one `record_curator`, capture the actual child/thread ID, verify its configured role instructions
and effective tools, prove it cannot recursively spawn, and prove bounded wait/stop behavior.
Only after that proof may the dashboard gain one narrowly allowlisted read-only execution adapter
with input/state/policy revalidation, explicit launch consent, idempotent request identity, real
job/events/results and no canonical data writes. Existing admin preview/confirmation/receipt
remains the only approved mutation path; an agent cannot synthesize `human_verified`.

An Agents API/SDK integration is a separate alternative, not an implicit fallback. It introduces
a new runtime and can introduce API billing, tool credentials and session persistence, so it
requires its own approved integration and cost/security review before implementation.

Until unblocked, the playbook must continue to report `NOT_CONNECTED`,
`dispatch_enabled=false`, and `job_id=null`. A drafted task is not dispatched, running,
independently verified or applied. Source runs, review dispositions, code work and committed
admin operations remain separate authorities.
