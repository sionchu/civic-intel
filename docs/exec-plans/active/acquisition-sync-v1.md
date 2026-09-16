# Acquisition Sync v1

Status: local implementation and verification complete; CI/delivery receipt is pending.

Baseline: `origin/master` at `cd0ea4fdbd4a1e970ee3399bdc79bc23aa95628b`.

## Objective

Add the smallest operational entry point for rerunning one already-approved L3 source:

```text
SourcePolicy
→ existing National Assembly collector/enumerator
→ SourceRun / SourceCheckpoint / SourceSnapshot / FeederObservation
→ existing deterministic materialization
→ existing Claim / ClaimEvidence publication gate
```

This is a source-specific sync boundary, not a new feeder, crawler, scheduler framework or
persistent sync model. The existing immutable observation rule remains authoritative: the same
`MONA_CD` plus normalized hash is unchanged; a changed normalized record creates a new immutable
observation version. Fetch time alone never creates a CHANGE, and provider record changes are not
silently classified as corrections.

## Source selection

Selected: **National Assembly current roster** (`national_assembly_members`,
`current_member_roster`).

Reason: the official API SourcePolicy, credential boundary, unfiltered provider-declared roster
coverage, `MONA_CD` provider identity, pagination checks, SourceRun/Checkpoint persistence,
resume/idempotency regressions and source-specific materialization/publication gate already exist.
The actual staging roster has already been materialized and browser-verified in the preceding
milestone; this execution will not fetch or write staging. ALIO current executives is deferred:
its L3 observation contract is valid, but its existing materialization action is intentionally
`REVIEW_REQUIRED`, so it is not the smallest first sync that reaches the existing canonical
publication path.

Excluded: new credentials, BTIS, CleanEye, MPM, asset disclosure, new HTML/browser crawler,
new public pages, portraits, Organization/issue/admin/community/MCP work and Railway changes.

## Implementation boundary

- Add one thin `workers.sync` command: `civic-sync assembly-roster [--resume]`.
- Use the existing `AssemblyRosterEnumerator.enumerate_and_materialize()` path; do not copy its
  parser, persistence or materialization logic.
- Report source, scope, run timestamps/status, observed/committed/unchanged counts,
  materialization conflict/review counts, checkpoint and redacted error reason from existing
  `SourceRun`/`SourceCheckpoint` values.
- Keep publication failures distinct from empty results in the command result/exit behavior;
  preserve the existing per-observation transaction rollback and never claim a successful sync
  after an exception.
- Add no schema or dependency. A transient CLI result/formatter is allowed; no persistent sync
  manifest or generic scheduler is justified by one source.

## Required scenario evidence

Use the existing Assembly fixture regressions as the canonical behavior proof and the thin
boundary regression as the command/result proof. The sync boundary does not duplicate the
enumerator's persistence or materialization tests:

- [x] first sync: `test_sync_boundary_reports_operational_receipt_and_materialization`
- [x] unchanged sync: the same test's second invocation reports `committed_count=0`,
  `unchanged_count=3`, and `AUTO_LINK=3`; existing `test_successful_rerun_and_changed_observation...`
  proves no duplicate canonical facts.
- [x] changed provider version: `test_changed_provider_record_creates_immutable_observation_version`
  proves a new immutable observation without overwriting the old version.
- [x] interrupted/partial run: `test_partial_failure_keeps_committed_checkpoint_and_resume_completes`
  and `test_checkpoint_does_not_advance_when_page_persistence_fails`.
- [x] resume: `test_partial_failure_keeps_committed_checkpoint_and_resume_completes` and
  `test_resume_materializes_prior_committed_page_and_new_page_only_after_success`.
- [x] idempotent rerun/materialization: `test_successful_rerun_and_changed_observation_are_idempotent_and_linked`.
- [x] fetch/parse/coverage, DB/precondition, publication and empty-result handling remain
  fail-closed and distinct in the receipt boundary; source-specific existing regressions cover
  API/policy/coverage and publication rollback, while the CLI emits a redacted failure receipt.

## Receipt and failure semantics

The command is intentionally source-specific. A successful receipt exposes the existing
`SourceRun` counters and the committed `SourceCheckpoint` cursor, plus the materialization
decision counts. `resume_requested` records operator intent without becoming a new persistence
key. An unchanged fetch still completes as `SUCCESS`, but has zero created observations and does
not create a new canonical fact or CHANGE.

Failure output has overall `status=FAILED` and a redacted `error_reason` phase. The phase is one
of `policy`, `source_fetch_parse_or_coverage`, `database_or_precondition`, `publication` or
`unexpected`; the persisted `SourceRun` status and checkpoint remain separately visible. A
publication failure can therefore show `status=FAILED` with `source_run_status=SUCCESS`: source
capture completed, but canonical publication did not. Empty provider coverage is a source
coverage failure, never a successful zero-result sync. Raw exception text, credentials and full
request URLs are never emitted by the boundary.

## Delivery loop

Implement one coherent slice, run targeted regressions, run the full local verification path,
inspect the Clean-v0 diff, update this plan and `HANDOFF.md`, commit/push to `origin/master`,
then record the actual CI Verify head/result. No staging execution is part of this plan.

## ASIDE A — visual read-only research

Review the existing `DESIGN.md` and current staging `/`, `/people`, `/people/[id]`, plus future
Organization/MONEY and evidence/source presentation. Return only KEEP / CHANGE / REMOVE / LATER
and a concrete wireframe proposal for a quieter editorial system. Do not modify UI code or
commit visual changes in this milestone.

### Result

- **KEEP:** the warm neutral canvas, Korean-safe serif display type, generous whitespace, thin
  separators, restrained emerald accent, semantic status colors, evidence-first proximity,
  single next action, explicit UNKNOWN/PARTIAL states, profile map and current card structure.
- **CHANGE later:** reduce nested rounded containers on People/detail; make identity, value and
  evidence type more editorial with flatter list rhythm; quiet secondary metadata; use fewer
  badges; allow subtle section transitions only with reduced-motion support. Reuse the same
  dossier rhythm for Organization and MONEY, with a compact `DERIVED · MONEY` module rather
  than a dashboard.
- **REMOVE:** no current surface requires removal. Do not introduce gradients, glassmorphism,
  neon/sparkle accents, KPI walls, excessive pills, heavy shadows or chatbot-first navigation.
- **LATER:** photography and image-led hero treatments remain behind a separate rights and
  identity gate.

Proposed future wireframe:

```text
global header: CI mark | People | quiet read-only status
home: small kicker → thesis heading → one how-to panel → one People action → sparse stats
people: kicker → heading/count/search → one quiet facet row → divider → flat identity cards
person: back link → name + RESOLVED → sticky profile map | coverage + claim sections → source library
organization/money: direct-ID dossier → annual Claim rows → compact DERIVED · MONEY comparison
```

## ASIDE B — portrait source-gate read-only research

Review the National Assembly official profile-image route and Wikimedia Commons for a possible
5–20 Person pilot: page/file identity, creator, license, commercial reuse, derivatives/crop,
attribution, stable version/file identity and withdrawal/replacement semantics. Do not select
or ingest images, infer identity from faces, modify code/DB/Git/Railway or add AI portraits.

### Result

- **National Assembly official route — NEEDS SOURCE GATE:** official member profile pages bind a
  page request carrying `monaCd`/term context to a profile image rendered as a CSS background
  under `/static/portal/img/openassm/new/`. The current connector does not expose or persist a
  portrait field, and the opaque image filename is not a provider identity. Two official pages
  produced different opaque image paths, but the path itself did not disclose `MONA_CD` or a
  version contract. This is a useful reconnaissance signal, not a closed acquisition contract.
  Review examples: [current Assembly profile](https://www.assembly.go.kr/members/22nd/KANGKYUNGSOOK/)
  and the [official copyright policy](https://assembly.go.kr/portal/bbs/B0000051/view.do?cl1Cd=&edate=&nttId=3869667&pageIndex=1&pageUnit=10&sdate=&searchCnd=1&searchDtGbn=c0&searchWrd=).
- **Rights:** the official policy permits free use of Secretariat-owned material only when the
  work carries the applicable KOGL mark, with source attribution; unmarked material requires
  prior consultation. KOGL Type 1 allows commercial use and transformation when that type is
  actually attached, but no such marking was assumed for a member profile image. No portrait
  enters the product until the individual asset's mark/owner/attribution and crop/derivative
  terms are recorded.
- **Wikimedia Commons — NEEDS FILE-LEVEL REVIEW:** Commons is not one blanket license. The
  [reuse guidance](https://commons.wikimedia.org/wiki/Commons%3AReusing_content_outside_Wikimedia/en)
  requires per-file license/creator review and other personality, privacy or moral-rights
  checks. The [Imageinfo API](https://www.mediawiki.org/wiki/API%3AImageinfo/en) exposes a file's
  canonical title, URL, timestamp, uploader, size, MIME and SHA-1; retain those as file/version
  evidence if a pilot is ever approved. Stable filename guidance does not eliminate file
  replacement or deletion risk; consult [file history/metadata guidance](https://commons.wikimedia.org/wiki/Commons%3AFile_naming)
  and the [deletion policy](https://commons.wikimedia.org/wiki/Commons%3ADeletion_policy/en).
- **Operational gate:** a 5–20 person pilot would need an exact canonical Person ↔ official
  page/file crosswalk, creator and license record, commercial/derivative/crop decision,
  attribution text, file URL/title, revision/upload timestamp, hash/dimensions, and a
  withdrawal/replacement response. A changed file revision, deletion, or withdrawal is a new
  review/version event and must fail closed until re-approved. Never choose the first search
  result, use face recognition for identity, or generate a replacement portrait.

## Verification record

Record local fixture, local runtime, CI and staging/deployed evidence separately. The final
report must include the selected source, current/changed path, scheduling boundary, every sync
scenario result, failure semantics, schema/dependency impact, both aside findings, tests/CI and
exactly one next action.

Current record: targeted Assembly batch/evidence/materialization regressions passed (`28 passed`)
after the boundary implementation. Full Python passed (`352 passed, 1 skipped, 4 warnings`),
Ruff passed for `apps packages workers tests`, mypy passed for `60 source files`, Golden quality
passed, web lint/typecheck/tests/build passed (`9` web tests), `.railway` standalone contract
check passed, and a disposable SQLite Alembic upgrade/downgrade/upgrade round trip passed.
`git diff --check` passed. No staging execution, deployment, database reload or Railway change
was made. The CI Verify result and final delivery SHA are recorded after push.
