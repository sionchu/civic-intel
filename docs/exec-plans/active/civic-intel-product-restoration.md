# Civic Intel product restoration

Status: LOCAL_CODE_DONE / TEST_PASS / BROWSER_PARTIAL / HOSTED_NOT_RUN. Owner: MAIN,
2026-10-08. The full contract is not complete. User authorized implementation and
multi-agent work under the full-goal execution contract after the read-only RCA.

## Objective and scope

Restore evidence-backed discovery, careers and official connections in 모두의국감,
using Civic Intel's canonical Claim/Evidence/Source/SourcePolicy chain. Gukgam 2026
is the entry point, not the permanent product boundary. Preserve the North Star's
long-term identity, activity, money, change and issue direction without advertising
unimplemented feeds or inventing records.

Canonical PostgreSQL writes, real identity/publication decisions, new image reuse,
hosted D1 binding/import/activation, Sites save/deploy, public access and paid resources
remain separate owner decisions. Local code and disposable-fixture verification are
authorized. No operational service or other worktree is modified.

## Baseline and ownership

- Remote master: `339363f5cf35502abb14fc2af04ed629a7ee8250`.
- Integration base: RELEASE-01 `31e1d7ae84aa970e722cfa8b4eccf156961541eb`;
  PR #204 remains draft/open on `feat/sites-storage-split-v1`.
- MAIN: isolated `codex/civic-intel-full-goal`; person UI, relationship transport,
  API/publication boundaries, integration, HANDOFF and this plan.
- CI-FULL-M2-UI: isolated `codex/civic-intel-discovery-ui`; home, roster, KST,
  DESIGN/Frontend Direction, predicate labels, styles and existing UI tests.
- CI-FULL-M3-CAREER: isolated `codex/civic-intel-career-projection`; career projection,
  profile regression tests and producer inventory.
- CI-FULL-M4-M5: source/risk review followed by narrowly assigned Gazette URL and
  portrait validation fixes, then independent career review and disposable QA fixtures.
  No network, credentials, human attestation or operational data writes delegated.
- Independent quality review follows integration. No recursive delegation.
- Original Windows checkout has an existing `contracts.py` edit and `.worktrees/`.
  Mac RELEASE-01 is at `f4d63bc` with eight modified files and one new replay helper.
  Both are preserved. Claude polish `4debb20` is inspected, not blindly cherry-picked.

## Milestones and acceptance

| Milestone | Work and acceptance | Current state |
|---|---|---|
| M0 | Recheck Git/PR, public/API counts, source seams and owners | API 1,142 public People; Sites D1 bindings empty; branch states rechecked |
| M1 | Reuse RELEASE-01, verify code/data separation, lifecycle, source closure, route/browser parity; prepare supported hosted writer decision | Local Worker build and pinned 50-path DTO parity PASS; native 390px blocked, real largest-page comparison NOT_RUN, hosted writes not authorized |
| M2 | Source-backed home brief, working exploration, precise filters, positive records before coverage | CODE_DONE; local verification and Aside acceptance below |
| M3 | Source-specific careers and bounded relationships through API, export, D1 and UI | CODE_DONE; API→D1 50/50 DTO equality on pinned synthetic QA; operational apply NOT_RUN |
| M4 | Exact-ID rights-reviewed photos, coverage/withdrawal evidence and eligible additional-file review | Existing one-photo contract hardened and tested; actual coverage expansion BLOCKED_BY_RIGHTS/IDENTITY/PUBLICATION |
| M5 | Gazette packet privacy/rights/identity proof, then eligible money publication and read slice | L1 privacy hardening tested; actual packet and money slice BLOCKED_BY_RIGHTS/IDENTITY/PUBLICATION |
| M6 | Further change/comparison/issues, API/MCP and community with scoped methods/rights | PLANNED, not advertised as live |

M1 retains its storage-specific contract in [Sites storage split](sites-storage-split-v0.md).
This plan owns integration and product scope, not a second storage implementation.

## Verification contract

- Career fixtures preserve attributed CLAIM, historical FACT, coarse periods,
  missing dates, identity, source conflicts and publication exclusion.
- Relationships preserve both endpoint Claim/Evidence/Source paths, typed via,
  rule version, DERIVED status and unknown temporal overlap; default excludes candidates.
- Export and replay use the same bounded query and include every cited Source.
- Photo and money absence never means a substitute portrait or zero personal assets.
- Narrow tests, `make verify`, final diff review and independent review.
- Aside-only desktop 1440px and native/top-level 390px, navigation/search/keyboard,
  evidence drill-down, errors, long records, version mismatch and withdrawal.
  Existing iframe evidence is not native mobile QA; HTTP/build is not visual PASS.
- Record code tests, browser proof, hosted preview, activation and deployment separately.

## Current checkpoint

Integration keeps one public transport and existing profile producer. No new canonical schema,
external publication, identity merge, operating DB write or collector was added. The only
local data writes were disposable QA fixtures and Miniflare D1. Final verification is recorded
below. This is a local review candidate, not an operational data refresh or release receipt.

### Goal coverage and remaining visibility gaps

| Capability | Operational baseline / why not visible | This candidate |
|---|---|---|
| Person / organization discovery | API has 1,142 public People; live Sites version 3 predates this candidate | Source-backed brief, exploration and exact committee facets staged |
| Legislative activity / votes | Existing published producers; static artifact grows with dense rendered records | Existing behavior retained; code-only Worker reused |
| Party / historical scope | Current Assembly facets apply only to their source scope; historical party is not current membership | Korean predicate labels and scoped filter copy staged; no name merges |
| Career | Biography/NEC/historical Claims previously missed career producer allowlist or source date rendering | Exact contract pairs, coarse date units and provenance connected locally |
| Official relationships | API existed; frontend and exporter did not consume it | Bounded include_candidates=false query, both endpoint Claim links and Source closure staged |
| Portrait | One local eligible exact-ID image; additional source rights not established | Existing image retained; withdrawal, no bytes for inactive/unlisted records, zero-eligible handling tested |
| Personal declared assets | Packet importer stops at Source/Snapshot/Observation; /assets=[] and no eligible real published Claim | URL privacy hardened; NOT_IMPLEMENTED real materialization/read slice remains blocked before rights/identity/publication |
| Organization MONEY / other money | Existing institution comparison is distinct from personal wealth; no new compensation/ownership producer approved | Existing behavior retained; no zero or inferred personal wealth |
| CHANGE / issues / community / API-MCP extensions | Source availability and methods vary; further product scope is not implemented | Existing CHANGE retained; additional work PLANNED (M6) |

### RCA-led changes and independent review

- Career worker commit `9967c93`, discovery worker `effa985`, source-boundary worker `edbadff`,
  storage tests `4ac3170` were read and integrated with scoped ownership.
- Independent read-only career review ran 40 tests with no actionable finding. A separate
  reviewer found source precision leaks, wrong same-page Claim links, false empty summaries,
  duplicate IDs, incorrect overlap type labels and lost PARTIAL section status. These were
  corrected and behavioral regressions added. Final targeted re-review is recorded below.
- A relation's API dates are conservative overlap bounds. UI labels them **비교 경계**, never
  source-stated month/year dates; career periods preserve each endpoint's own precision.
- The existing photo was opened and inspected, SHA-1 remained
  `46f16ce27199a761bb472cb0f68a763a3afa16db` (38,558 B). No new photo rights were asserted.
- Gazette URL allowlist rejects unknown/duplicate parameters, fragments, userinfo and invalid
  ports. Only canonical safe URL text persists. Synthetic secret canaries are not emitted.
- Default npm 11.6.2 failed strict generated-lock validation. Supported cached npm 11.21.0
  built successfully; a later registry re-resolution failed ETARGET. Builder now accepts an
  explicit previous successful generated lock, always validates it through npm ci, and
  invalidates a previous success marker before a potentially failing ci. No install fallback.
- Windows Turbopack rejected the external node_modules junction. It was detached without
  removing its target and replaced with an independent local copy; original release worktree
  dependencies remain intact. A running Worker preview also held dist files; only this task's
  preview was stopped before rebuilding.

### Current pinned QA input and evidence

All files below are local ignored artifacts under `dist/full-goal-evidence/`; they are not
published receipts. The separate fixture worktree's `dist/full-goal-fixture/receipt.json`
labels its data **DISPOSABLE_SYNTHETIC_QA_NOT_OPERATIONAL_OR_PUBLICATION_APPROVAL**.

- Fixture API source archive: `0708bf30ed512fe1a2b4517a54c78ec348b5e837`, Alembic head `0008`.
  Golden 10 + clearly named synthetic 3 = 13 public People, 6 Sources, 50 exported paths.
- Export: `projection-qa/projection-manifest.json`, snapshot `ps-5cb225217ae02703`, generated
  2026-10-08 15:42 KST. Synthetic month CLAIM/conflict, past-term FACT, two same-name IDs,
  exact committee relation with temporal UNKNOWN. No source collection or human review claimed.
- `api-d1-parity.json`: all 50 exact API JSON DTOs equal decoded active Miniflare D1 values.
- `web-tests.log`, `make-verify*.log`, `next-build.log`, `worker-*-build.log` retain executed
  outcomes, including failed attempts; final results below supersede only the same checks.
- Aside `aside-home.log` and `aside-search.log`: actual 1440x900 top-level viewport, homepage,
  Enter search → query-preserving People results, 3 synthetic matches, two distinct same-name
  links. Home screenshot opened and visually inspected (2160x1350 raster at device scale 1.5).
- Screenshot source:
  `C:/Users/getch/.aside/u/0/sessions/2026-10-08_Aw8EoMWPi9mTjOtr/artifacts/civic-full-home.png`.
  Full-page capture fell back to a viewport capture; do not label it a full-page image.
- Initial Person capture timed out in Aside. The subsequent DOM run opened relation evidence
  and the matching Claim disclosure, but its test expected a supplementary container that
  this fixture did not need; this is a harness assertion error, not a product PASS. Fresh
  final person proof and any capture result are recorded below.
- Native 390px: BLOCKED by current Aside API (`setViewportSize` absent). No alternate browser
  or iframe was substituted. Full real 1,142-person/largest-page parity for this modified
  candidate is NOT_RUN; prior RELEASE-01 evidence is historical, not reused as current PASS.

### Final local verification receipt — 2026-10-08

- Code integration commit: `5f61f728d39773a7601c770a29832456173206e7` on
  `codex/civic-intel-full-goal`; committed `apps/web` tree
  `b2f51ffb3741619a1068be11d6e5a406d8394081`.
- `make-verify-final.log`: exit 0; ruff PASS, mypy 152 files PASS, Python **1,116 passed /
  3 skipped**, Golden Set PASS, web **73 passed / 0 skipped**, Next and standalone PASS.
  This full run preceded the final UI-only false-empty fix. After that fix,
  `web-final-ui-fix.log` reran lint, typecheck, all 73 web tests, Next build and standalone
  validation successfully. Backend was unchanged and its long suite was not repeated.
- `worker-final-ui-fix.log`: actual code-only Worker build, strict npm ci with the retained
  generated lock, disposable D1 load and activation PASS. Artifact **1,744,138 bytes /
  146 files**, 0 prerendered HTML, 0 per-record RSC text. Lock SHA-256
  `ce7c560997eaa6e216898203cdc27e71c914033ec355031cc6ffade47a7c361c`.
  The artifact manifest honestly records pre-commit `0708bf3` plus dirty working tree;
  those tested code contents were subsequently committed as `5f61f72`. It is not a
  clean-HEAD hosted release artifact. Projection manifest SHA-256
  `467520ea6973b605f6acc8dfe79bf04b30f4e6451559c4e4493e2dfdeeab2baa`.
- `civic-final-person-proof.json` and `aside-final-person-proof.log`: final Worker/Next
  main text and href arrays match; Claim IDs are unique; relationship evidence opens the
  correct Claim; false empty direct-connection copy is absent when a derived relation
  exists; 1440x900 viewport has no horizontal overflow. No pageerror was observed during
  these interactions (listener was attached after navigation).
- `civic-navigation-errors.json` and `aside-navigation-errors-final.log`: past term is
  **2012.05.30 – 2016.05.29 / FACT / 역대 국회의원 임기**. Header navigation, browser
  back and forward reached their expected URL and fresh rendered state. Aside's back and
  forward wait functions each timed out; the subsequent snapshots confirm actual navigation,
  so retain both UI-state success and runner errors. Missing ID shows the not-found page.
  Stopping only the disposable API caused Next to show **SERVICE_UNAVAILABLE**, not UNKNOWN
  or an empty result. Worker continued reading the pinned local D1 snapshot.
- `home-1440.png` and `career-1440.png` were actually opened and inspected. These are
  viewport captures, not full-page images. A later attempted connections capture fell back
  to the footer viewport and does not prove connection layout. The first final interaction
  attempt timed out after its disclosure remained closed; the fresh final proof above passed.
  Native 390px, full-page capture, live 1,142-person/largest-page parity, and complete graph
  interaction remain outside this browser receipt; overall browser acceptance is PARTIAL.
- Final diff inspection and `git diff --check` passed. Independent reviews were advisory;
  MAIN verified each fix. Original Windows checkout remains `a2766da` with the same
  `contracts.py` edit and `.worktrees/`; original RELEASE-01 remains clean at `31e1d7a`.
- Task-owned fixture API 8127, Next 3137 and Worker 8797 were stopped after QA; no listeners
  remained on those ports. Other services and worktrees were preserved. No push, merge,
  operational DB write, new image publication, Site save, hosted activation or deploy occurred.

### Hosted writer and approval boundary

Installed Sites storage contract supports logical DB binding plus schema-only migrations.
Available connector tools expose database overview/row reads, save/deploy and access control;
no supported arbitrary bulk SQL writer was found. Fresh read-only overview still had no D1
binding and Site version remained 3. Local SQL imports do not establish hosted access.

Prepared inputs are the existing schema migration, exporter load/activate/rollback SQL,
public-boundary validation, and code-only Worker artifact. A hosted proposal must identify an
actual supported writer, owner-only authorization, credential handling, exact snapshot hash,
staged validation, atomic activation receipt and prior snapshot rollback. A public import
endpoint, hidden migration seed or invented Sites route is not an approved substitute.
Saving a Site version, binding DB, loading/activating hosted data and deploying remain NOT_RUN.

M4/M5 needs a separately approved source packet: exact official Gazette issue/PDF hash,
rights attestation, human comparison of permitted totals in THOUSAND_KRW, source period/type
and family-included-total annotation only, followed by exact Person linkage and publication
approval. The existing synthetic 2099-1 fixture is not that packet. SourcePolicy can_send_to_ai
restrictions remain in force; do not use AI to manufacture human review.

## Next concrete action

The next unresolved browser acceptance step is native 390px Aside verification, followed by
the real largest-page comparison against this candidate's pinned source/data. Resolve an
actual supported owner-private hosted writer before preparing a concrete DB/Sites cutover
approval. M4/M5 needs the owner-approved rights/identity/publication packet described above;
until then, do not claim actual photo coverage expansion or a live personal-assets slice.
