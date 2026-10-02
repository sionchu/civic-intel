# Mac SSD database and Sites delivery

Owner selected this topology on 2026-10-02: the Mac runs the canonical DB/API from its
external SSD; the cloud web surface will use Sites later. The local runtime milestone is
verified. Cloud connectivity, Claim publication, Workers output and Sites deployment remain
separate unfinished stages. See [the executed receipt](../receipts/mac-ssd-site-20261002.json).

## Current topology

```text
Frozen successful Assembly capture (299 observations)
  → SQLite online backup preserving canonical IDs and provenance
  → /Volumes/data/civic-intel/service/assembly.sqlite (schema 0008, mode 0600)
  → canonical identity service: 298 Persons and DRAFT Claims; one OPEN conflict
  → canonical API, read-only SQLite connection, 127.0.0.1:8765
  → later: authenticated HTTPS connection and Sites Worker frontend
```

The original acquisition file is unchanged by SHA-256. Its three Sources/Snapshots,
SUCCESS run and complete 299-record checkpoint remain intact. The service DB is 1,409,024
bytes and the SSD had approximately 2 TB free at postflight. No provider request, source key
read, cloud DB write, cloud-corpus migration or automatic Person merge ran in this milestone.
The existing Railway corpus and protected backup are preserved; this is an Assembly-only
target, not a replacement copy of all 9,120 existing cloud Persons.

MAIN is the sole allocated writer. The deterministic materialization was a separate command:
`civic materialize assembly --allow-effect IDENTITY_MATERIALIZATION --database-url
sqlite:////Volumes/data/civic-intel/service/assembly.sqlite`. It ran from the existing installed
wheel in a deny-network sandbox with the source-key directory unreadable and writes limited
to the allocated SQLite files. The source agent prepared/reviewed the path without keys or
operational access. No collector schedule or DB-enforced shared-writer lease was introduced.

All 298 Claims are DRAFT and have ClaimEvidence→Source→SourcePolicy. Read-only publication
preflight found 298 technically eligible role Claims, but changed no publication status and
made no human-review attestation. The remaining observation is OPEN with
`EXACT_BIRTH_DATE_CONFLICT`; do not resolve it by name or merge it automatically.

## Runtime and recovery

The API reuses the installed wheel at code `333aa26` because its API/application/persistence
code is identical to current base `0865e5d`; all 147 installed Python files match the pinned
wheel. The web UI is a separate artifact and is not installed by that Python wheel.

The new [launcher](../../scripts/mac_ssd_api.py) checks the mount, allocated VolumeUUID,
file ownership/permissions/device and schema 0008. It never provisions or migrates. It strips
inherited credentials before even invoking diskutil, opens SQLite with `mode=ro&uri=true`,
and exposes only the existing public API defaults on loopback with one worker. Admin/review
surfaces stay disabled. Stable process-state output omits SQL arguments and tracebacks.
The request wrapper returns 503 after the DB disappears or its inode/device changes.

The owner-approved Python removable-volume access was followed by a successful separate-port
LaunchAgent probe. The permanent user service `com.civic-intel.ssd-api` was then enabled and
bootstrapped on port 8765; its owned temporary processes were stopped. RunAtLoad and failure
restart are configured. Actual logout/reboot and physical SSD disconnection were not executed.
An earlier background attempt waited inside SQLite open and was unloaded; its precise cause
was not independently established. Do not grant broader disk permissions as a workaround.

Checks from the Mac: `/health`, `/ready`, `/people` and a Person detail return 200; directory
count is 298. Detail Claims remain empty because DRAFT is excluded. Admin/review, missing
Person and a Source reachable only from DRAFT Claims return 404. Listener inspection confirms
127.0.0.1 only. An actual SSD disposable backup fixture proves missing/replaced file→503 and
a SQLAlchemy read-only connection rejects a write. Physical unplugging was not used as a test.

For ordinary local inspection, run API requests through Remote Desktop Commander on the Mac.
For its service, inspect `launchctl print gui/501/com.civic-intel.ssd-api`; unload only that
owned job for maintenance with `launchctl bootout gui/501/com.civic-intel.ssd-api`.
Preserve the runtime receipts and the frozen acquisition file. After a disk identity, schema or
file replacement mismatch, inspect before restarting; do not create a fallback DB on the Mac's
internal disk or blindly restart a source collector.

## Sites MCP and SDK findings

The installed Sites plugin provides native site registration, source credentials, version save,
private deployment, deployment status and environment operations. These management tools do
not require an app-level MCP server, Agents SDK or an OpenAI model API key. No Site has been
registered or deployed for this repository. A later Site starts owner-private and retains that
audience unless the owner explicitly changes it; every Sites deployment URL is production.

Official OpenAI tooling is documented in [openai/sites](https://github.com/openai/sites):
`@openai/create-sites` scaffolds projects and `@openai/sites-vite-plugin` packages hosting
metadata into the build output. Its [package documentation](https://github.com/openai/sites/tree/main/packages/sites-vite-plugin)
shows `import { sites } from '@openai/sites-vite-plugin'` in Vite configuration, requires
`.openai/hosting.json`, and distinguishes simulated local identity from production. The installed
Sites starter vendors plugin 0.2.0. Reuse the connector's provisioned Site identity and native
workflow; do not replace this canonical UI with a new starter merely to use the SDK.

Sites server code must be Cloudflare Worker-compatible ESM with a default callable `fetch`;
the current Next standalone server is not such an artifact. Sites guides prohibit raw TCP
connections and direct using HTTP APIs for external services. The SSD DB stays on the Mac;
no D1 copy or remote SQLite file share is needed for the selected topology.

[Cloudflare's Next guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/)
documents Vinext for existing Next 16 applications. Registry inspection found Vinext 1.0.1,
Node >=22 and Vite 8 peers. The executed `npm exec --yes --package=vinext@1.0.1 -- vinext check`
reported 12 supported checks, zero partials/issues, five supported import families and seven
pages. This is a static compatibility result, not a Workers build, runtime or visual acceptance.
It did not modify package manifests/lockfiles, initialize Vinext or create a parallel frontend.

Sites documentation/capabilities checked here do not establish private Mac/LAN connectivity.
A cloud Worker cannot reach the Mac's loopback address. Before connection, prepare and review
an authenticated HTTPS route to the same Mac API: fixed origin, server-held credentials,
bounded GET routes/timeouts, no admin/review/source-collection routes and no DB port exposure.
Do not send a source API key to Sites or treat Sites visitor identity as a Mac service credential.
Confirm any hosting/account cost and access change from its concrete configuration.

## Next delivery steps

1. Prepare the exact Claim/profile publication selection and retain the OPEN identity conflict.
   Technical eligibility is not publication approval; keep the current DRAFTs unchanged.
2. Adapt and verify the same UI's Workers build using the official Vinext/Sites tooling,
   preserving the existing Next development/release path and canonical DESIGN/API contracts.
   Complete the outstanding Aside rendered/mobile gate for the Person UI.
3. Verify the selected secure HTTPS connection and actual Site-to-Mac reads. A connector/MCP
   invocation does not establish network reachability or authorize public API exposure.
4. When the later Sites publication stage is approved, use one native registration, the exact
   pushed source, the bundled site-workflow build/archive validation, private save/deploy and
   terminal deployment status. Do not bypass native tool approvals or register another App.

SDK investigation and local runtime preparation are complete; publication and the full
Person→Claim→Evidence→Source site acceptance remain incomplete.

The next server-call preparation and frontend/backend choices are documented in
[the integration plan](FRONTEND_BACKEND_INTEGRATION.md). It extends the same web client;
the earlier runtime receipt remains unchanged historical evidence.
