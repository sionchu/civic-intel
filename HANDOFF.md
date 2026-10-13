# HANDOFF

## Objective

Complete the 2026-10-13 audit follow-up and the October14 instruction to continue actual source collection: align current state, capture the permitted selected records, prepare one genuine asset disclosure for identity review, bound Person browser delivery, and add an evidence-backed vote-record comparison. 국감 is an entry point, not the permanent product boundary.

## Scope

Current work order: [product restoration](docs/exec-plans/active/civic-intel-product-restoration.md). The owner's 2026-10-14 “마저 진행해 수집까지” additionally authorizes bounded, policy-permitted operational ingestion. Preserve exact stored source policies, identity, publication and privacy gates. No fabricated human review, public release or paid-resource change is implied.

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
- October13 PETI candidate preview: DRY_RUN, one record, no write, identity confirmation or publication. October14 source-only capture is recorded below. [Exact review item](docs/research/PETI_ONE_RECORD_REVIEW_2026-10-13.md).
- Person delivery selects 20 records per server query before client serialization. Exact Claim/Source selection, legacy hashes, search, paging and visible input drift remain supported. D1 pins the immutable snapshot ID, including Source-only corrections.
- Read-only two-Person vote comparison at /compare/votes: explicit period, exact event intersection, excluded/one-sided counts and both evidence paths. No scores or inferred absence reason.
- Sole approved R-ONE catalog packaged as a resource with preserved LF/hash. Native Windows private-key-file loading explicitly rejects before file access; wheel/checkout byte verification passed.
- Independent reviewer findings resolved; final review found no remaining blocking code defect.

## Current checkpoint

| Layer | Last evidence | Interpretation |
|---|---|---|
| Integration | origin3295ad9 fetched2026-10-13 | Follow-up local implementation verified; visual/release gates open |
| Schema/DB | Final Mac read2026-10-14:0008; 9,758 people; 809,624 Claims; 905,764 observations; 13,042 snapshots | +27 observations/+2 snapshots; Person/Claim counts unchanged |
| Public reader | Fresh 10/13 Aside DOM: 1,142 people; footer 2026-10-09 10:18 KST; no comparison/market menu | Public code/snapshot ID not re-read; local changes not deployed |
| Public export | 10/8-9: 1,142People/387Organizations/795,154Claims/2,478Sources | Historical inventory, not today's DB totals |
| Gazette | 10/13 parser merge, operator-reported284/284 | REVIEW_REQUIRED; no publication inferred |
| PETI candidate | October14 exact reviewed policy registered; one immutable metadata observation committed | Identity link and publication NOT_PERFORMED |
| R-ONE/market | October14 read-only actual SQLite:32 snapshots/observations,64 successful runs,0People/Claims | Existing isolated L2 corroborated; NOT_L3/NOT_PUBLISHED |
| Core collection | Fresh receipts: roster299, bills19,876, meetings1,964; ALIO/MOIS successful declared scopes | Completion is scoped, not all-source completeness |
| Votes22 | October14 completed interrupted refresh:1,911/1,911; last run298,100 unchanged,0created; one source conflict retained | SUCCESS; no active SourceRun or acquisition lock |
| Official press | Fresh October8 selected page:26/26 provider rows committed,26 new observations | SELECTED_PAGE_ONLY; no identity link or Claim |

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

Human review, publication, deployment, changed-product-code PostgreSQL/container execution, hosted peak/storage measurements, and desktop/mobile pixel review. Canonical inventory and source acquisition began2026-10-14 under the new explicit instruction; see the collection checkpoint below.

## Collection checkpoint — 2026-10-14

Mac canonical DB backup completed:pre-codex-collection-20261014-004141.dump,302,562,335 bytes; pg_dump and archive-list validation exit0. No restore test claimed. Existing backups/deployed code preserved. Existing stored Assembly SourcePolicy is passed unchanged and matched on each commit; source content and credentials remain outside model/tool output.

Source-only operator PID92628 uses the shared scheduler lock and canonical repository/helpers from an existing verified worktree. Press run894bc34e-a3f9-41d0-94f5-031d831d099a committed26 observations, snapshot SHA256bb29e7e5bc6d5dcd36d3b2b85f61894a06b8fbff97c419be5eecc00bd94c94dc. October8 provider total is now26; the older10-row receipt is stale. Vote resume is bounded to1,053 bills plus at most3 universe-page requests; fingerprint drift fails closed.

First operator exited2 correctly: free space fell below1GB, vote runbbd502a7-00f1-4aa8-9176-30024486ee8e ended PARTIAL at909, zero new vote versions; no active run/lock remained. DB size increased only32,768 bytes; the broader disk-pressure cause is unproven. Space later recovered to2.8GB without deletion. The owner then explicitly approved moving backups to the external drive. Eleven files (2,294,095,608 bytes, including one pre-existing zero-byte file) were copied to /Volumes/data/civic-intel-backup-relocation-20261014 and every SHA256 matched again before removing only those original copies. Original backups path now symlinks to the verified external directory. Relocation exit0; internal free space5.1GB. No database files moved.

Continuation PID94609 uses the same lock/guard and resumes at909 with1,002-bill budget. Exact PETI metadata policy registration used a fresh canonical preview and owner-authorized collection actor; human_verified=false. Capture run37319e58-a763-4cd7-b814-f158ca6a47a4 created one observation/snapshot f7b3650b-ac39-4b75-832c-88ec107cf33c, metadata hash082cb44a566e643bc0f52a237fa5d4ab72386acda7091929be9c2f127e130b71. No Person linkage or Claim publication. The existing candidate policy note describes its historical staging origin; current collection authorization, not that note, authorized registration. Fetch/fulltext/excerpt/commercialization remain false.

PID94609 exited2 after an AssemblyApiError before advancing909. After backup relocation, PID95050 completed the same bounded continuation with no automatic per-request retries: exit0, SourceRun99483577-e856-4028-a90a-e417ba5b31a5 SUCCESS, checkpoint1,911/1,911,1,002bills and298,100unchanged votes,0created. The October11 prefix255,383 + October14 first segment15,166 + final298,100 =568,649 records. One SOURCE_CONFLICT remains explicit. This is completion of the interrupted refresh, not568,649 newly created records.

Final read-only DB verification confirmed SUCCESS, finished timestamp and checkpoint.last_run_id match,0RUNNING runs, released acquisition lock, unchanged Assembly policy,9,758People/457Organizations/809,624Claims (801,008PUBLISHED;8,616DRAFT),905,764observations and13,042snapshots. Internal free space6.18GB. Full count-only receipts, backup hash manifest and final read are preserved in dist/collection-2026-10-14/final-evidence.json and the Mac operator directory. Existing R-ONE isolated database proof remains32observations,64successful runs,0People/Claims; no new market acquisition or public release.

Narrow tests80 passed (press32, PETI48); operator syntax passed. Independent read-only review found an exit-status aggregation issue and a missing exact-admin-action guard in continuation; both were corrected before their respective executions. Output receipts remain metadata/counts/hashes only. Durable final run status was independently re-read. Product code and schema were unchanged; the earlier full product suite was not rerun for these operational/documentation updates.

Independent PostgreSQL READ ONLY verification (PID97288 exit0): press/PETI runs both SUCCESS;27/27 observations join Snapshot→Source→Policy; fulltext0, PersonObservationLinks0 and related ClaimEvidence0. Source URL credential contamination0. Assembly policy hash unchanged55ff4207b089789d83a3d4abe54ca0a823e735b49edaf9f9eaeacd79ffff1b90; PETI permission flags match the exact candidate. The transaction was rolled back without writes.

## Blockers

PETI's genuine owner identity review and subsequent exact link/publication decisions remain pending. Source-only capture is complete; it cannot supply human_verified. See the exact record review item above.

Public release remains unapproved. Aside visual/mobile verification must finish first. Baseline npm audit also reports 9 dependency findings (8 high / 1 critical, including direct Next); this task did not change dependency versions or establish exploitability. Preserve dist/continuation-evidence/npm-audit.json and resolve the affected dependency release gate before deployment.

## Modified files

MAIN owns state/comparison/integration. Product builder owns Person delivery. Runtime builder owns pinned catalog packaging and explicit credential-platform handling. Git diff is the exact integrated inventory.

## Next concrete action

Confirm the exact PETI record identity through genuine human review; separately finish the visual gate and baseline dependency remediation before proposing public release. Do not restart feature expansion or claim full product completion.
