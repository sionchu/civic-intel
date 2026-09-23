# Native admin agent execution prerequisite

Status: BLOCKED; request preparation is delivered by
[the completed playbook slice](../completed/admin-work-playbook.md), not an execution system.

## Observed prerequisite

The installed Codex0.154.0 native probe exposed `collaboration.spawn_agent`, but did not expose
or prove a named-role configuration selector. A task_name is not that selector. Zero children
were launched; effective child tools/credential restrictions were not verified. This is evidence
about the tested invocation, not proof that every Codex interface lacks the feature.

Project role files remain canonical in `.codex/agents/` and `docs/roles/ROLE_MODEL.md`.
No wrapper/harness replacement, broad credential inheritance, extra provider login or lowered
sandbox protection is authorized to bypass the missing proof. A shell read-only label does not
isolate an independently authorized MCP, remote desktop, account or operational DB.

## Smallest unblocking proof

Use a disposable workspace with synthetic inputs and no operational credentials. Prove the native
selection/loading of one configured read-only role, actual child ID, observable allowed tools,
no recursive spawn, bounded timeout/cancel and structured result. The parent must not substitute
a generic task name or paste a marker to claim that a role file was loaded. Capture the effective
runtime configuration without printing secrets. Check the supported current client/schema rather
than assuming a flag or UI version enables the capability.

Only after that proof, implement one narrowly allowlisted read-only adapter with input/state/policy
revalidation, explicit launch consent, idempotent request identity, real job/events/results, and
no canonical data writes. Existing admin preview/confirmation/receipt remains the sole approved
path for mutations; human_verified cannot be synthesized by an agent.

Until verified, the playbook correctly displays execution NOT_CONNECTED, dispatch_enabled=false,
job_id=null. Source runs, review dispositions, code work and committed admin operations remain
separate authorities. A drafted task is not dispatched, running, independently verified or applied.


A follow-up synthetic probe on2026-09-24 used only a disposable workspace and provided prompt,
ignored user-wide config, disabled apps/plugins/shell/browser/computer tools, and tested the installed
native multi_agent_v2 feature without changing project/global settings. It again returned BLOCKED:
no role selector in collaboration.spawn_agent, no child ID, no configured marker returned and zero
children launched. This confirms the tested route still does not justify enabling live dispatch;
it does not prove that every native interface or future client has the same limitation.
