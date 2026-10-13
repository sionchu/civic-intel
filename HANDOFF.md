# HANDOFF

## Objective

Complete the 2026-10-13 audit follow-up: align current state, prepare one genuine asset disclosure for review, bound Person browser delivery, and add an evidence-backed vote-record comparison. 국감 is an entry point, not the permanent product boundary.

## Scope

Current work order: [product restoration](docs/exec-plans/active/civic-intel-product-restoration.md). Preserve source policies, exact identity, publication and privacy gates. No canonical mutation, fabricated human review, public release or paid-resource change is implied.

## Acceptance criteria

- Code, running API, data and public delivery have separately dated evidence.
- Asset preparation produces a no-write preview and names the actual missing human decision.
- Person delivery selects bounded records before browser serialization and retains every eligible record, exact links and version-conflict handling.
- Vote comparison declares period, common inputs, exclusions, methodology and both evidence paths.
- Full canonical checks and independent review; Aside UI/behavior evidence recorded separately.

## Completed

- Fetched origin and pinned 3295ad9e4604b5d113c44244be0457aef3fa8270 (2026-10-13).
- Baseline GitHub Verify 38286145216 succeeded: Python 1,465 passed / 3 skipped; web 108 passed / 1 skipped; PostgreSQL 3 passed plus migration/backup/restore.
- Preserved original master a2766da, contracts.py change and untracked worktrees/report.
- Isolated codex/civic-product-completion; full-goal 2b77944 is already integrated remotely.
- Prior HANDOFF and restoration plan preserved verbatim in docs/history.
- Real PETI candidate default preview: DRY_RUN, one record, no write, identity confirmation or publication. [Exact review item](docs/research/PETI_ONE_RECORD_REVIEW_2026-10-13.md).
- Person delivery selects 20 records per server query before client serialization. Exact Claim/Source selection, legacy hashes, search, paging and visible input drift remain supported. D1 pins the immutable snapshot ID, including Source-only corrections.
- Read-only two-Person vote comparison at /compare/votes: explicit period, exact event intersection, excluded/one-sided counts and both evidence paths. No scores or inferred absence reason.
- Sole approved R-ONE catalog packaged as a resource with preserved LF/hash. Native Windows private-key-file loading explicitly rejects before file access; wheel/checkout byte verification passed.
- Independent reviewer findings resolved; final review found no remaining blocking code defect.

## Current checkpoint

| Layer | Last evidence | Interpretation |
|---|---|---|
| Integration | origin3295ad9 fetched2026-10-13 | Follow-up local implementation verified; visual/release gates open |
| Schema | 0008 in code/prior runtime | Running DB not re-read now |
| Public reader | Fresh 10/13 Aside DOM: 1,142 people; footer 2026-10-09 10:18 KST; no comparison/market menu | Public code/snapshot ID not re-read; local changes not deployed |
| Public export | 10/8-9: 1,142People/387Organizations/795,154Claims/2,478Sources | Historical inventory, not today's DB totals |
| Gazette | 10/13 parser merge, operator-reported284/284 | REVIEW_REQUIRED; no publication inferred |
| PETI candidate | Existing permitted receipt, fresh no-write preview | Current canonical bridge NOT_REVALIDATED |
| R-ONE/market | Selected-scope local L2; no eligible public map figures | NOT_L3/NOT_PUBLISHED |

## Decisions and reasons

One current checkpoint lives here. [Prior receipts](docs/history/handoff-through-2026-10-09.md) are historical evidence, not renewed permissions. Person browser delivery is bounded while the unchanged snapshot still requires full server-side Person decoding. Live HTTP has no immutable snapshot ID, so its version guard covers Person/profile/related DTOs but cannot guarantee Source-only drift detection. D1 uses its request-pinned immutable snapshot ID. Comparison pins the Claim inputs it actually displays; linked evidence is separately re-read.

Legacy static HTML export now stops before acquisition/output because query-based record windows require a server runtime. Next standalone and the official D1 Worker build both passed. Do not publish the old static export or mistake its guard for an exporter regression.

## Verification evidence

- Baseline CI: https://github.com/sionchu/civic-intel/actions/runs/38286145216
- Prior audit LF-blob Windows narrow suite:162 passed/1 failed (POSIX credential permission check).
- PETI: dist/continuation-evidence/peti-one-record-preflight.json, SHA256 dcc02df6f3d4a92ec343b9440aa7cb56ea65115282fd99b71f5fad47695b6120; exit0, DRY_RUN, no DB/network.
- Changed code: all Makefile verify constituents executed directly in Windows PowerShell with the existing venv. Ruff, mypy, pytest, quality, web lint/typecheck/test/build passed; standalone asset check passed.
- Python: 1,473 passed / 4 skipped (3 PostgreSQL tests: no POSTGRES_TEST_URL; 1 native POSIX permission test: Windows). Total derived from complete pytest progress/exit0 because repository quiet flags suppress the final count. POSIX rejection semantics and unsupported-platform fail-closed cases did execute. Logs: dist/continuation-evidence/{ruff,mypy,pytest,quality}.log.
- Web: 123 passed / 0 skipped after the real Vinext runtime became available. Logs: dist/continuation-evidence/web-*.log. Initial 122/1 result is superseded only for this unchanged test/code set.
- Official Sites Worker: strict ci, Worker TypeScript, Vinext build and public boundary checks passed. Artifact: dist/continuation-worker/worker-manifest.json; 168 files / 6,499,426 bytes. Build records a92aa6c plus the then-uncommitted comparison; this is a local candidate, not a deployed receipt.
- Worker npm 11.6.2 generated-lock failure was resolved using existing npm 11.21.0; product dependencies were unchanged. Logs: .pytest_cache/continuation-worker-build*.log. Real Vinext request-cache/snapshot checks: 10 passed / 0 skipped.
- Synthetic scale fixture: 1,910 votes; initial selected evidence 22 Claims / 22 Sources / 45,401 bytes versus 3,529,861 bytes of full Claim input. This is serialized evidence size, not total network size, latency or production performance.
- Aside DOM behavior: native comparison form, 1,910-result page2 (20 rows), exact off-window Claim open with evidence, last-record search, keyboard submission with settled 0-match explanation, off-window Source, and stale Person version rejection passed. Logs: dist/continuation-evidence/aside-{comparison-behavior,person-behavior,search-confirmed}.log.
- Visual gate: UI_VERIFICATION_INCOMPLETE. Aside screenshot timed out; setViewportSize is unavailable. No desktop-pixel/mobile visual PASS. Intermediate search snapshots were stale or transient; only the settled final DOM supports keyboard/filter success.
- Next build first failed EBUSY because the local standalone preview held its output directory; stopped only that preview, rebuilt and reran standalone check successfully.
- History archive contents equal origin3295ad9 (normalized line endings). Original checkout remains untouched.

## Not executed

Canonical writes, new acquisition, human review, publication, deployment, current DB inventory, changed-code PostgreSQL/container execution, hosted peak/storage measurements, and desktop/mobile pixel review.

## Blockers

PETI's genuine owner identity review and exact policy/capture/publication decisions remain pending. Parsing success cannot supply human_verified. See the exact record review item above.

Public release remains unapproved. Aside visual/mobile verification must finish first. Baseline npm audit also reports 9 dependency findings (8 high / 1 critical, including direct Next); this task did not change dependency versions or establish exploitability. Preserve dist/continuation-evidence/npm-audit.json and resolve the affected dependency release gate before deployment.

## Modified files

MAIN owns state/comparison/integration. Product builder owns Person delivery. Runtime builder owns pinned catalog packaging and explicit credential-platform handling. Git diff is the exact integrated inventory.

## Next concrete action

Confirm the exact PETI record identity through genuine human review; separately finish the visual gate and baseline dependency remediation before proposing public release. Do not restart feature expansion or claim full product completion.
