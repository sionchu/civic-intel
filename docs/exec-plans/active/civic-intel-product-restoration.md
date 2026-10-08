# Civic Intel product restoration

Status: LOCAL_CODE_DONE / TEST_PASS / REAL_PUBLIC_API_CONTENT_PASS / BROWSER_PARTIAL / HOSTED_NOT_RUN.
Implementation owner: MAIN; 2026-10-08 follow-up execution/integration owner: GPT-6.1 Sol,
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
| M1 | Reuse RELEASE-01, verify code/data separation, lifecycle, source closure, route/browser parity; prepare supported hosted writer decision | 5,170 real public-API response hashes/Source-reference closure, largest Person/Org SSR–Worker content parity and local rollback round trip PASS; real visual NOT_COMPLETED, native390 USER_DEFERRED, hosted NOT_RUN |
| M2 | Source-backed home brief, working exploration, precise filters, positive records before coverage | CODE_DONE; local verification and Aside acceptance below |
| M3 | Source-specific careers and bounded relationships through API, export, D1 and UI | CODE_DONE; synthetic50/50 and existing real public API5,170/5,170 DTO parity incl1,142relationship paths PASS; real browser both Claim endpoints PASS; CURRENT_PRODUCER_FULL_CHAIN missing, operational apply NOT_RUN |
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

### Follow-up execution checkpoint — 2026-10-08

The owner assigned execution/integration, browser QA and readiness work to actual
`gpt-6.1-sol` agents; root Astra orchestrates and adjudicates scope only. The prior MAIN
implementation receipt above remains historical. This follow-up verifies real public data and
fixes the measured Source anchor offset; producer semantics and persistence schema are unchanged.

- Clean code input `cd8cdcc610f09717765b02f1cca8b5f87332dfa2`, web tree
  `b2f51ffb3741619a1068be11d6e5a406d8394081`. `worker-clean-head-build.log` records strict
  npm ci, Worker typecheck/build, public boundary scan and disposable D1 activation. Manifest
  `worker-clean-head/worker-manifest.json` records `git_worktree_dirty=false`, **1,744,138 B /
  146 files**. The generated Sites source ZIP is **900,768 B / 91 files**, SHA-256
  `a897484fa54f9a09a23ca53568f689a6eedeb300964d657fa22c59c8b71d1193`; it excludes DB and
  node_modules and is not a hosted deployment artifact or receipt.
- Exact build command from `apps/web`: `node scripts/build-sites-worker.mjs --lockfile
  .sites-worker-build/package-lock.json --out ../../dist/full-goal-evidence/followup/worker-clean-head
  --load-local ../../dist/full-goal-evidence/projection-qa`, with the previously verified npm
  11.21 CLI selected by `npm_execpath`. Lock hash remains the prior `ce7c5609...361c`.
- `next-clean-head-build.log`: current Next production build and standalone preparation PASS;
  standalone contract check PASS. `storage-clean-head-tests.log`: **7 passed, 0 skipped**.
  Full `make verify` is **NOT_RERUN**: the initial capture/build checkpoint changed no product
  behavior; the later Source-anchor fix is CSS-only and passed the 50 affected UI regressions,
  lint, both fresh production builds and targeted Aside checks. Backend contracts, schema and
  producer logic are unchanged. The prior full result above is not relabeled as a fresh full run.
- `browser/synthetic-acceptance.md` records current desktop relationship disclosure, keyboard
  Enter, both endpoint Claims, Source cards/policy, direct graph with complete accessible list,
  and Worker/Next main-text/href/ID parity PASS on `ps-5cb225217ae02703`. Two viewport screenshots
  were captured and actually opened. Prior harness selector/quoting errors remain in logs.
- Native top-level 390px is **USER_DEFERRED**, following the owner's explicit instruction.
  `browser/aside-capability-recheck.json` retains the supported-API limitation separately.
- Existing Mac API freshly returned ready and **1,142 People**. Operational checkouts/services
  were preserved. The older real capture remains `ps-b0a439f3b8327121`: manifest SHA-256
  `6594e56b02f3e90d114d1e0db622451911f5608402ac618bb33cf52f221cf526`, load SQL SHA-256
  `f38499a1cce7c3422b1476e71f071610bfa86c3b611fa1ba7e9e7736dfe0e26d`. It omits this candidate's
  bounded relationship paths and is not reused as current acceptance.
- **PASS (capture and exact transfer)**: only the current exporter, public-boundary and relationship-path modules were
  copied into isolated `/Users/lee/Projects/civic-intel-full-goal-qa-20261008`. LF-normalized
  SHA-256 values match the current code input; see `exporter-source-receipt.json`. Command:
  `node apps/web/scripts/export-public-projection.mjs --api http://127.0.0.1:8100 --out projection
  --concurrency 2`. Capture began **2026-10-08T09:12:58.325150Z**. It uses no DB credential,
  source collector, canonical write or operating-service reconfiguration. The exporter writes
  only after all public reads complete. It finished at **2026-10-08T09:38:47.087Z** with
  1,142 People, 387 Organizations, 578 Sources, 5,170 paths and 386 contract-valid money 4xx.
  Snapshot `ps-65e086d2eb00c3c5` has semantic SHA-256
  `65e086d2eb00c3c51a1b18042cfdd75fb4494fb77f2304702cca577f834ca1cc`.
  The post-capture roster matched captured bytes; all 4,028 legacy common tuples were unchanged,
  and 1,142 bounded relationship paths were added. This is still not atomic capture evidence.
  Original manifest SHA-256 is `439b83094ae1451f671399f34869ca69e024a1b20e2bf36b882eb3ad9f8f781f`;
  original load is 224,391,271 B, SHA-256
  `b9c2f047eeb96516f10f4f6d725d2d410ed517f0b07363a9460b79287d227ef1`.
  A first positive-offset file transport produced mismatched bytes and was rejected before SQL
  execution. Offset-zero transport of 76 immutable, individually hashed chunks recovered exact
  original bytes. Both failure and recovery receipts are preserved in `real-public-capture/`.
  Canonical local replay/export reproduces all 5,170 `(path,status,SHA-256,JSON bytes)` tuples.
  Platform compression differs: original 7,514 parts / 110,765,264 gzip B; local 7,449 parts /
  108,552,232 gzip B. `real-reexport-parity.json` preserves separate file hashes. Full original
  and local response decoding/hash, public-boundary scan and captured Source-reference closure
  passed. Final browser content/behavior acceptance and local lifecycle are recorded below.
- `real-d1-staged-state.json` and `real-d1-staged-integrity.json`: canonical local Wrangler load
  exited 0; real data is STAGED while the synthetic pointer remains ACTIVE. Every 5,170 decoded
  response / 7,449 stored part and captured Source-reference closure passed. The first ignored
  verifier assumed ACTIVE; its failed log is retained, and the explicit STAGED verifier passed.
  Canonical exact-byte activation SQL exited 0; `real-d1-active-state.json` records real ACTIVE
  and synthetic PREVIOUS, retaining rollback target. Wrangler's character-wise quoted-blob SQL
  splitter consumed about 13 minutes before load completion; this is a measured throughput
  limitation, not a data correctness failure. No parser or persistence workaround was added.
- `real-worker-growth.json`: the same actual runtime artifact remains 150 files / **1,749,739 B**,
  tree SHA-256 `c4744769a26d7667629a75135c62bd604003fd7a0d0c26fb9aa3fb74ae6c750a`,
  **0 B growth** from 13 to 1,142 People. This runtime measure includes four preview scratch
  files and is separate from the clean 146-file / 1,744,138 B build receipt.
- Failed temporary transfer chunks remain preserved: the guarded PowerShell cleanup command
  was rejected before execution with `blocked by policy`, without a more specific reason.
  Cleanup is **NOT_RUN**; no alternate command or transport was attempted.
- Largest-page pre-fix Aside QA found a Source title behind the sticky header after settled
  anchor navigation. The canonical `.source` now uses the existing **104px** anchor offset,
  matching evidence panels and profile sections. `source-anchor-ui-tests.log`: 50 passed;
  `source-anchor-lint.log`: exit 0. Fresh clean code **145348b39669d4ace75901dfb4dba1dd2afb50db**,
  web tree `c7da9663dc195bf567b7336939ceffc6a86d0f0e`, passed Worker strict-ci/typecheck/build and
  Next production build/standalone checks. Final clean Worker is **146 files / 1,744,186 B**;
  actual preview runtime is **150 files / 1,749,787 B**, tree SHA-256
  `6723db29c03fb4a3d7ce47d18fc0645d583d01f34d1f6c5b6e49be5546afde19`.
  Generated source ZIP is **91 files / 262,639 B**, SHA-256
  `3940bcd91009ae12f784569d73cb481e3d4f925352b0004b92b8fc2dd0633625`.
  `source-anchor-package-receipt.json` and `source-anchor-runtime-tree.json` preserve provenance;
  this is a source package, not hosted deployment. D1 retained real ACTIVE after rebuild.
  `browser/final-browser-acceptance.md` records post-fix native 1440x900 Aside content/behavior
  **PASS**: complete main textContent/innerText/ordered hrefs/IDs match Worker and SSR for the
  largest Person (7,083,370 JSON B) and Organization (894,831 JSON B). Person has 3,099,982 text
  characters, 7,213 links, 2,383 Claim anchors, 36 Sources, two graph edges and 12 relationship
  rows; Organization has 546,565 characters, 825 links and 410 Claims. IDs are unique, no dangling
  same-page fragments or horizontal overflow were observed. Source titles are visible after
  settled Person navigation on both ports and Organization keyboard navigation. Earlier Org
  pointer navigation had the correct hash but offscreen target and remains **INCOMPLETE**.
  Real Worker graph/list, both endpoint Claims with CLAIM/SUPPORT, roster 1,142 unique links,
  and home name-search Enter returning the exact Person passed after actual readiness.
  **Visual acceptance NOT_COMPLETED**: bounded real Person/Org and even small-home screenshots
  timed out. Opened loading/synthetic screenshots are not current real visual acceptance.
  This does not establish an independent performance acceptance or a screenshot-related product
  defect. No further unchanged-input capture retries or speculative pagination refactor occurred.
  The old `cd8cdcc` candidate and pre-fix browser receipts remain historical evidence.
- Dataset acceptance is **CURRENT_FRONTEND_PUBLIC_API**. Upstream API runtime revision is
  **UNKNOWN**, and consistency is **UNVERIFIED_CAPTURE_WINDOW** (not a DB transaction).
  Current candidate producer runtime is **NOT_VERIFIED / NOT_APPLIED_BY_THIS_TASK**. Public Source-reference
  closure and token scanning do not independently revalidate rights or canonical publication.
  **CURRENT_PRODUCER_FULL_CHAIN** remains separate missing evidence; public DTOs intentionally
  omit canonical SourcePolicy and cannot safely reconstruct that gate.
- `readiness/owner-review-packet.md` and `sites-readonly-state.json`: fresh owner/public/version 3,
  no D1 binding/table and no exposed Sites-managed bulk writer. Required owner-scoped writer
  contract, immutable load/validation/atomic activation/rollback inputs, one bounded additional
  portrait candidate and the seven-part Gazette approval packet are concrete proposals only.
  No photo expansion, raw PDF processing, human attestation, hosted write/save/deploy or access
  change occurred. The existing portrait is **38,558 B**, SHA-1
  `46f16ce27199a761bb472cb0f68a763a3afa16db`; local integrity does not refresh remote rights.

All new paths in this checkpoint are relative to ignored `dist/full-goal-evidence/followup/`.
Real full-transfer/hash/Source-reference closure and exact replay-export tuple parity passed.
Local real activation and full ACTIVE decoding passed; post-fix largest-page content/behavior
comparison passed with visual limits above. Real pointer rollback restored synthetic ACTIVE
and retained real PREVIOUS; both decoded integrity checks passed. A retry of `activate.sql`
exited 0 but left PREVIOUS untouched because its guard requires STAGED. The actual ACTIVE
postcondition correctly failed; `real-d1-reactivation-noop-receipt.json` preserves this lead
recipe error. Canonical real `rollback.sql` then exited 0 and restored real ACTIVE with synthetic
PREVIOUS. `real-d1-restored-final-state.json`, `real-d1-restored-final-integrity.json` and
`real-d1-restored-final-runtime-retention.json` prove **PASS** for the complete round trip,
5,170 exact response hashes / 7,449 parts, 578 captured Source-reference closure, and unchanged
150-file / 1,749,787 B final runtime. The restore SQL state guard and SHA were checked against
actual ACTIVE/PREVIOUS states (`real-d1-restore-transition-precondition.json`). No product or
SQL-library change was made. Owned previews on 8127/3137/8797 are stopped and all browser task
tabs closed. Original Windows and Mac checkout changes are preserved. Temporary cleanup is
NOT_RUN_TOOL_POLICY_DENIAL. `followup-acceptance-receipt.json` consolidates these evidence classes.
Capture integrity PASS is not complete frontend or producer-chain acceptance.

### Hosted writer and approval boundary

Installed Sites storage contract supports logical DB binding plus schema-only migrations.
Available connector tools expose database overview/row reads, save/deploy and access control;
no native arbitrary bulk SQL writer was found. The 2026-10-08 investigation verifies documented
`env.DB.prepare()/batch()` and owner-private dispatch service-access primitives; this is not an
installed or authorized writer for the current public project. Fresh read-only overview remains
owner/public/version 3, access revision 2, no D1 bindings/tables. Local SQL imports do not
establish hosted account access or ownership of a runtime visitor principal.

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

### Hosted writer read-only preflight — 2026-10-08

**READ_ONLY_PREFLIGHT_COMPLETE / PROVIDER_CONTRACT_REQUIRED / HOSTED_NOT_RUN**. Clean input
`ac2eccab7168e2bd1edc579c19ea2f0db8bef144`; product code remains `145348b` with the same web tree.
`dist/full-goal-evidence/hosted-writer-investigation/pinned-preflight.json` verifies exporter LF
SHA `95846fd8af8b98d8ec0ba847810d2f68a2d33f0587bc1fb460628b340c28bb5d`, both manifest hashes,
original/local load hashes, all 5,170 response tuples and existing source ZIP hash. No refresh,
import, credential generation, Site mutation or external inquiry ran.

`measure-sql.py` executed against existing files and read-only SQLite; `sql-measurement.json`
and `statement-batch-inventory.json` preserve exact hashes/offsets without printing SQL bodies.

| Local artifact | Bytes | SQL statements | Largest statement B |
|---|---:|---:|---:|
| load.sql | 219,947,725 | 7,487 | 80,275 |
| validate.sql | 220,537,529 | 7,487 | 80,354 |
| activate.sql | 220,538,210 | 7,490 | 80,354 |
| rollback.sql | 220,538,013 | 7,488 | 80,354 |

Maximum gzip BLOB is 40,000 B; scope metadata is 727,132 B. Individual statements fit the
[100,000 B SQL and 2 MB value/row limits](https://developers.cloudflare.com/d1/platform/limits/).
The full activation SQL contents alone are 220,530,628 B: buffering the entire statement array
is incompatible with the documented [128 MB Worker isolate](https://developers.cloudflare.com/workers/platform/limits/).
Whole batch duration is limited to 30 seconds; Sites dispatch/account limits remain UNKNOWN.
All SQL files fit the documented 5 GB direct-file import size, but Sites-managed account/resource
authority and its whole-file transaction/receipt contract are NOT_VERIFIED.

One local Wrangler `batch()` method call contains 7,490 SQL statements. Do not equate these
units: D1's 50/1,000 query wording and newer Workers subrequest defaults differ; exact Sites/D1
statement versus API-call accounting is **PROVIDER_CONFIRMATION_REQUIRED**, not a proven
7,490-statement rejection. [D1 batch](https://developers.cloudflare.com/d1/worker-api/d1-database/#batch)
provides one transaction, not a transaction spanning requests. Hypothetical 16-statement
descriptors require 469 activation calls with at most 1,285,562 SQL B each; this is planning
inventory, not a writer implementation or measured hosted performance.

`reviewable-recipe.md` preserves the conditional canonical extension: bounded typed parts,
pinned full manifest/metadata, STAGED-only writes, durable seal and transactional validation
cursor, final atomic expected-pointer transition/readback, exact PREVIOUS restore and separate
bounded retention/GC. Current unconditional ON CONFLICT prevents overwrite but not extra-key
append; full metadata assertions and in-flight-reader retention would also need review for a
future multi-request writer. These are future protocol risks, not failures of the trusted exact
local file/exclusive lifecycle already verified. No speculative schema, parallel importer or
public write endpoint was added. Tests/build/browser are **NOT_RUN this investigation** because
product code/schema/runtime are unchanged; the executed evidence is read-only measurement,
hash preflight, official/installed-document review and sanitized native Site state.

Installed documents do not verify management-owner to Site-scoped runtime-principal mapping,
another private project's authority over this DB, or a same-public-project owner-private hosted
writer. Service access supplies no visitor identity. The current Site audience was preserved.
`supported-path-assessment.md` and `read-only-provider-state.json` contain the exact live and
installed-contract evidence; no claim of absolute platform impossibility is made.

## Next concrete action

The owner explicitly deferred native 390px on 2026-10-08 (`USER_DEFERRED`); the current Aside
capability limitation remains recorded and does not block the authorized desktop follow-up.
Next task only: obtain the provider's **same-project owner-only write-authority contract**.
The following inquiry is prepared for copying; it has **not been sent**:

> 프로젝트 `appgprj_6ac46916b4d08191872983ffd6d52aba`의 현재 public audience/version 3을 유지하면서, 정확한 Sites-managed D1에 owner-only로 적재·검증·원자적 활성화·롤백할 수 있는 공식 지원 경로를 확인해 주세요. 관리 owner와 runtime principal의 검증된 매핑 또는 플랫폼 owner-only enforcement, 정확한 DB/binding 쓰기 권한(다른 private project를 제안한다면 명시적 공유 권한), 비밀값 없이 사용 가능한 credential 방식, request/memory/time 및 SQL 문장 수와 batch API 호출 수의 제한 단위, immutable load·idempotent resume·validation-to-activation exclusion·실제 상태 readback/rollback receipt 계약과 읽기 전용 확인 방법을 제공해 주세요. 직접 administrative file import를 지원한다면 Sites 계정/DB 권한과 whole-file transaction/receipt 및 R2/cost 조건도 명시해 주세요. 접근·배포·binding·적재 변경은 이번 문의에 포함되지 않습니다.

No hosted cutover is authorized. Producer full-chain, real visual capture and M4/M5
rights/identity/publication remain the acceptance gaps above; native390 remains USER_DEFERRED.
