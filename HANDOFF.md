# HANDOFF

## Objective

Continue the Assembly site pilot with owner-selected option1: canonical DB/API on the Mac
external SSD, cloud web on Sites later. The SSD runtime milestone and official Sites SDK
investigation are complete. The pilot is IN_PROGRESS: 298 identity-linked DRAFT Claims are
private; Claim publication, cloud connectivity, Workers output and rendered/mobile acceptance
remain incomplete. Prior Opus UI code and the existing Railway corpus are preserved.

## Scope

Preserve Evidence Core, current Organization/source reachability, UNKNOWN, admin signing/locking/
receipts, source-context identity gates and schema compatibility. Preserve original master edits
and the successful Mac SSD capture. Source, identity, publication, release and recurring collection
are separate effects. No production, new domain/indexing, public API/DB or paid plan change.

## Acceptance criteria

Current pilot acceptance: full code/Golden gates, canonical source coverage/provenance,
gated identities/Claims, exact SSD identity/schema/read-only runtime, actual Aside desktop/
mobile/keyboard evidence, and verified Site-to-Mac reads at a reported deployed commit.
Code, original capture coverage, private identity/DRAFT construction and local API checks
passed. Publication, cloud reachability, Workers build, visual acceptance and deployment
have not passed. Earlier PostgreSQL backup/restore evidence remains historical evidence.

## Completed

All five milestones in docs/exec-plans/completed/architecture-current-master.md. Eight adapters,
nine enumerators sharing SourceLifecycle, 37 CLI routes, startup readiness only, policy-first
identity, local trace/run correlation, old paths removed and full histories retained.
Separate collector preparation, immutable Mac runtime and bounded acquisition are complete.
One live run completed; coverage, provenance, privacy and zero identity/publication rows were audited.
The approved single source key has been delivered privately from Windows to Mac without printing
its value or transferring other `.env` values.

## Current checkpoint

Branch codex/architecture-current-master, isolated architecture-current-master worktree.
SSD implementation base 0865e5dec85b043574640dc02132366631ce7b11.
UI commit af46132d49d0e8106851c473bfcda69c50f89345, on approved work-order commit 4c947e9.
Current plan: docs/exec-plans/active/assembly-site-pilot.md.
Current receipt: docs/receipts/mac-ssd-site-20261002.json.
Runtime/delivery guide: docs/operations/MAC_SSD_SITE.md.
Mac service DB: /Volumes/data/civic-intel/service/assembly.sqlite, schema 0008, mode 0600.
Consistent SQLite backup preserves the successful 299-observation capture and its canonical
IDs/provenance. Separate deny-network/key-denied materialization produced 298 Persons,
298 DRAFT Claims, 298 Evidence/links; one OPEN EXACT_BIRTH_DATE_CONFLICT remains unresolved.
Read-only publication preflight: 298 technically eligible, zero failures; no publication or
human-review attestation executed. Original capture SHA-256 unchanged.
User LaunchAgent com.civic-intel.ssd-api is enabled and running on 127.0.0.1:8765.
Health/ready/people/person return 200; directory 298; admin/review and DRAFT-only Source 404.
Temporary manual/probe services and the preparation REPL stopped; a fresh Commander process
confirmed the same permanent API remained ready. Actual reboot/logout and physical unplug
were not executed. Sites registration, HTTPS cloud connection and Workers output do not exist.

Preserved preceding staging receipt: docs/receipts/assembly-site-pilot-20261002.json.
Historical staging schema 0008; public 299; People 9120, Claims 14397, Organizations 347.
One authorized source run 876cd05a-973a-4375-8432-26d90c87bae4 ended PARTIAL/ConcurrentWrite.
Checkpoint page 1 and manifest 100/299; zero new observations, one snapshot and one run committed.
Historical PG logs identify file extension/No space left on device; data FS 100%, available 552960
bytes, configured volume 500 MB. The SSD decision supersedes resize/recollection proposals.
Do not materialize/publish from the incomplete Railway checkpoint or retry it.
Base/remote master 77e2767ab043738f00b8dd38be8d99803e5ad7bc; verified source
333aa26bda5f1110e53190f27de0c62a0f43cb30 for the installed bounded candidate; initial
architecture source 0ae6945 is retained in the earlier receipt.
Original master and its modified packages/domain/contracts.py remain untouched.
Mac bounded runtime: /Users/lee/Developer/civic-intel-collector-20261001/bounded-333aa26,
Python 3.12.14, pinned wheel. External /Volumes/data is APFS on USB 10 Gb/s. Owner node approval
resolved remote storage access; mkdir/fsync/readback/SHA/rename and SSD schema/CLI checks passed.
Target mac-ssd-assembly-one-shot-333aa26 is schema 0008, mode 0600. SourceRun
62f4567c-fb56-403c-952d-eb768136d6c3 is SUCCESS; 299 observations, three snapshots/Sources,
checkpoint 3, zero People/Claims/Organizations in the frozen capture. Parent launcher pin 7b004bf and SHA-256
33d50df5b38387c9ec7e7908fe168bd15e5dc10a585fc0d3d49be34520701662; wheel stays 333aa26.

## Decisions and reasons

Transform current semantics rather than replacing them from an older branch. Preserve existing
canonical rows and schema 0008. Dedicated immutable one-shot acquisition is the first collector
option; unrestricted LLM roles/worktrees cannot prove credential/tool isolation or writer exclusion.
The selected site API reuses the byte-verified wheel and canonical persistence; it neither
fetches nor writes. MAIN remains the sole allocated writer. No generic importer or cloud
corpus migration is implied. Native Sites management MCP needs no custom application MCP.
Official OpenAI Sites/Vite tooling and Vinext are the later Worker delivery path; the static
compatibility check does not prove a build or private Mac network connection.

## Verification evidence

SSD milestone: canonical fixture `make verify` runner exit 0, CANONICAL_VERIFY_EXIT=0;
862 Python PASS, 4 optional PG skips, 6 SQLite datetime warnings, 375.44s; Ruff, mypy
(146 files), Golden, architecture, 26 web tests, lint/typecheck/build and assets PASS.
Launcher-specific Ruff, Darwin mypy and nine focused tests PASS. Independent read-only
review independently ran those nine tests, matched the launcher hash and found no further
defect; the reviewer did not reproduce Mac operations. Actual SSD fixture: read-only write
rejected, missing/replaced file 503. Schema and source policy/provenance postflight PASS.
Owner reported Python removable-volume approval; separate login-service probe and permanent
bootstrap PASS. Fresh check after preparation process exit: ready 200, same permanent PID.
Official Sites SDK investigated; Vinext 1.0.1 static check exit 0: 12 supported, zero partial/
issues. No dependency manifest change, adapter initialization, Workers build or deployment.
Commands, timestamps, states and remaining gates: docs/receipts/mac-ssd-site-20261002.json.

Preceding staging/UI evidence (not re-executed optional PG runtime tests in this milestone):
Current UI: `python -X utf8 .tools/run_fixture_verification.py .tools/make/ucrt64/bin/mingw32-make.exe verify`
exit 0; 853 Python passes, 4 optional PG skips, 6 warnings, 26 web passes, lint/typecheck/build PASS.
Four optional PostgreSQL tests separately executed, exit0, in a new disposable local DB.
Private fresh dump/restore matches schema/counts/policy/coverage/provenance; dump 29465885 bytes,
SHA 92fa5661207325c60e30a515e02f16a44dbb4afa967357d5b37e90c88c4ef78d.
Actual Opus model claude-opus-5-5, exit 0; two turns, 240.641s, seven-file tool-less code packet.
Independent final diff review: no actionable regression. Offline 299-record PG rerun PASS: 6 snapshots,
299 observations retained, second-created 0/unchanged 299. No provider network or operational writes.
Aside production-artifact DOM confirms filtering, profile/audit/source-policy/UNKNOWN/PARTIAL,
final keyboard source hash and not-found; immediate mouse/scroll acceptance is unconfirmed.
Screenshots timed out; writable mobile viewport API absent. UI verification incomplete.
Exact 3-file UI patch applies to public master 77e2767, candidate bytes match. No public push/deploy.
Partial postflight checked 100 contexts and one new snapshot: policy/privacy violations 0, public 299.
Earlier pilot-owned loopback web/API/PG and private tunnels stopped; protected backup remains.

Earlier completed architecture/Mac evidence:

python .tools/run_clean.py .tools/make/ucrt64/bin/mingw32-make.exe verify: exit 0; Ruff, mypy
(146 files), 728 Python tests, Golden quality, architecture contract, web lint/types, 26 web tests
and standalone build PASS. Four PG cases skipped there were separately executed: 4 PASS/no skips.
Fixture PG18.6 migration/dump/restore: 0008, 16 People, 10 public People, 7 published Organization
Claims; clusters stopped and temporary password files removed. Final installed wheel outside
checkout: 37 routes, safe missing-key receipt, schema readiness and Alembic round trip PASS.
Full results: docs/receipts/architecture-current-master.md. Six SQLite datetime warnings retained.
Mac: venv install/pip check, 13 manifest hashes, 0008→0007→0008 and missing-key audit PASS.
Offline sandbox: six file/network checks and installed 37-route CLI/missing-key audit PASS.
Details, commands and limits: docs/receipts/mac-collector-readiness-20261001.md.
Bounded candidate after relay integration: full make verify passed 826 Python/26 web tests (4 optional PG cases skipped;
six SQLite warnings retained), mypy 146 files, quality/architecture/build. Independent read-only
review found no defect. Mac installed CLI proved 37 routes and SUCCESS/FAILED/PARTIAL/checkpoints
on four SSD mock fixtures. Forced-stop fixture proved RUNNING/RECOVERY_REQUIRED, no automatic retry.
Pinned relay 22d32c6 passed 58 offline tests and independent review. Seven Mac egress canaries
passed. Installed canonical CLI with real HTTPX/TLS passed trusted fixtures and rejected an
untrusted certificate; no official API or OS trust change. Approved request hash b127f5f1;
single-key encrypted delivery PID57756 completed with exit 0.
Updated inputs/receipts: docs/receipts/mac-collector-bounded-20261002.md.
Final launcher: 27 tests, Ruff and mypy-darwin PASS; independent read-only review pinned source.
Full gate after launcher integration passed 853 Python tests, 4 PG skips, 6 warnings and 26 web
tests. Final repeat at 7b004bf passed CANONICAL_VERIFY_EXIT=0. Tight Mac profile passed seven
canaries and actual installed CLI; real watchdog stopped/reaped its own child at 180.011s and
kept RUNNING/RECOVERY_REQUIRED in an isolated fixture. Approved live execution PID75766 exit0
in 3.44s; canonical audit PID76155 exit0. Actual provider coverage/provenance/privacy PASS.
Sanitized receipts copied byte-for-byte: docs/receipts/assembly-one-shot-live-20261002.json,
assembly-one-shot-live-audit-20261002.json and one-shot-profile-7b004bf.json.

## Not executed

Current-branch remote CI, cloud DB identity/admin writes, Claim publication, scheduling,
full rendered/mobile acceptance, conflict/loading/transport-error browser states, Docker build,
push/PR/merge, Sites registration/deployment, Worker build/runtime, authenticated HTTPS cloud
connection, cloud corpus migration, resize/plan or public access changes. No source retry.
Actual Mac logout/reboot and physical disk unplug; current optional PG runtime tests.

## Blockers

Sites cannot reach Mac loopback. A concrete authenticated HTTPS route, Worker artifact and
verified Site-to-Mac reads are required before cloud delivery. Sites inspected capabilities do
not establish private LAN connectivity. Claim/profile publication selection remains separate;
the OPEN birth-date conflict fails closed. Aside capture/mobile limitations block visual
acceptance. The preserved Railway volume is full, but resizing is no longer the selected path.
Allocated ownership is not a DB-enforced shared-writer lease; old ALIO/MOIS RUNNING records
remain preserved and do not authorize recurring writers.

## Modified files

This milestone adds scripts/mac_ssd_api.py and its focused regression coverage, SSD/Sites
operations guide and sanitized runtime receipt; updates this HANDOFF, active pilot plan and
INDEX. Previous UI commit contains the Person page, scoped CSS and copy-coupled UI assertions.
Diagnostic helpers, runtime databases/keys, raw model/browser outputs and private process logs
remain outside Git. Original root master/user contracts.py edits remain untouched.

## Next concrete action

Prepare the exact Claim/profile publication selection while preserving the OPEN identity
conflict; retain DRAFT until the separate publication gate is satisfied. Adapt the canonical
UI to Worker output using official Sites/Vinext tooling without replacing its architecture.
Complete actual Aside desktop/mobile acceptance. Prepare and review the concrete authenticated
HTTPS connection, cost/access and public-code scope before the later private Sites delivery.
Use native Sites registration/build/archive/save/deploy/status only at that later stage.
Preserve the frozen source capture, private service DB, healthy loopback API and Railway backup.
