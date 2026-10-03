# Canonical operator commands

The installed entrypoints are `civic` and the offline Golden evaluator `civic-quality`.
`civic inspect commands` prints the complete command/effect inventory without opening a
repository or loading a worker. This cutover removes the legacy console scripts; there
is no `civic-sync` alias. Use `python -m apps.cli` when running directly from a checkout.

Each command has one declared effect. `inspect` defaults to `READ_ONLY`. Every other verb
requires the matching `--allow-effect` on its lane command. A mismatched effect, unknown
flag, missing confirmation digest or invalid scope argument is rejected before worker
or repository dispatch. This effect declaration is an operator scope check, not source
rights, identity approval, human attestation, DB exclusion or publication permission.
Existing SourcePolicy and canonical worker gates still apply.

| Effect | Commands |
| --- | --- |
| READ_ONLY | `civic inspect ...`, `civic-quality` |
| SOURCE_INGESTION | `civic observe ...` including one-page/staging pulls that fetch sources |
| IDENTITY_MATERIALIZATION | `civic materialize ...` |
| CLAIM_PUBLICATION | `civic publish ...`, `civic review assembly-distinct-person` |
| SCHEMA_OR_DEPLOY | Reserved effect; no schema/deployment runner is exposed by this CLI |

For example:

```powershell
civic observe assembly --allow-effect SOURCE_INGESTION
civic materialize assembly --allow-effect IDENTITY_MATERIALIZATION
civic publish assembly-profile --allow-effect CLAIM_PUBLICATION
civic inspect alio-safe-people
civic materialize alio-safe-people --allow-effect IDENTITY_MATERIALIZATION --expected-receipt-sha256 <current-preflight-sha256>
```

The baseline Assembly distinct-Person review commits a published role Claim along with
the Person, so its current effect is CLAIM_PUBLICATION. An identity-only service split
must make the role Claim DRAFT before this route can be reclassified.

The separate Assembly materialization adapter consumes already persisted successful
coverage through `materialize_latest_successful(application)`. It never fetches and creates
DRAFT Claims. Claim publication is a separate explicit operation. For a reviewed draft use
`civic publish claim --allow-effect CLAIM_PUBLICATION --claim-id <draft-claim-id>`; the publication
gate is revalidated in the transaction that changes its status. Base-profile publication is a
separate source-specific operation. `civic inspect commands` inventories all current routes.

`civic observe mois-organization-lookup --allow-effect SOURCE_INGESTION --database-url
<exact-disposable-or-assigned-database> --full-name <exact-name> --expected-full-name
<same-exact-name> --page-size 100` captures one filtered first page for institution-code
review. Alternatively replace `--full-name` with `--org-code <seven-character-provider-code>`
and retain the expected full name. Exactly one filter is required; page size is 1–100.
There is no `--resume`, `--max-pages`, materialization or publication option. The distinct
lookup scope cannot advance the unfiltered `mois-organizations` L3 checkpoint. The output
contains aggregate coverage and exact-name counts in the capture; no exact name in a
truncated page does not mean absence. SourcePolicy/schema gates run before fetch; one
fetch uses the existing 15-second HTTP timeout. A live runner additionally needs its own
hard process budget and target/writer checks. See [the MOIS contract](../architecture/MOIS_ORGANIZATION_CODE_FEEDER.md).

`civic inspect gukgam-witness --allow-effect READ_ONLY --research
docs/research/gukgam_2026_science_witness_linkage_2026-10-02.json --plan-packet
tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json` prepares a local source-to-plan
label crosswalk. `--plan-packet` is repeatable on this inspect path only. The single witness
`--packet` form still requires its exact `--artifact`. No DB/source fetch occurs. All matching
schedule occurrences remain candidates, source dates stay separate and raw plan bytes/current
editions remain unverified. See [the witness contract](../architecture/GUKGAM_WITNESS_PACKET.md).

`civic observe gukgam-schedule-probe --allow-effect SOURCE_INGESTION --date YYYY-MM-DD
--committee <exact-committee> --page-size 10` fetches a bounded schedule sample without persistence.
It checks SourcePolicy before fetching. It remains an L1 discovery path awaiting approved live
validation; its effect is source acquisition even though it writes no database rows.

`civic observe assembly` accepts optional `--max-requests`, `--min-request-interval` (seconds)
and `--fetch-deadline-seconds`. Supply all three together: a positive integer request cap,
a finite nonnegative interval and a finite positive deadline. Invalid combinations fail before
worker/DB dispatch. Omission preserves existing behavior. Limits cover one connector lifetime;
the elapsed budget begins at first fetch, spaces attempted request starts and rejects expired
responses before page ingestion. The per-operation HTTP timeout is at most 15 seconds and
shrinks to remaining fetch time. This cooperative deadline does not bound worker parsing/DB
commit or guarantee process recovery. A budget stop records FAILED before any committed page
or PARTIAL after prior committed pages, retaining the last committed checkpoint. Numeric limits
do not grant source rights or permission to resume, materialize or publish.

## Complete legacy console-script map

The pinned `77e2767ab043738f00b8dd38be8d99803e5ad7bc` manifest contains **19** installed
console scripts, including `civic-quality`. The inventory below reflects actual source,
not an assumed count of 20. Direct `python -m workers.*` modes are listed where a script
formerly mixed effects. Add the matching `--allow-effect` shown above to every new
non-read-only command. Retain the listed scope/input flags on the new lane command.

| Old script and mode | New command | Preserved flags / change |
| --- | --- | --- |
| `civic-quality` | `civic-quality` | Offline Golden evaluation unchanged |
| `civic-stage-assembly` default | `civic observe assembly-page` | `--page-index`, `--page-size`, `--name`, `--party`, `--district` |
| `civic-stage-assembly --enumerate` or `--resume` | `civic observe assembly` | `--page-size`, `--resume`, `--database-url`; unfiltered universe |
| `civic-stage-assembly --enumerate --materialize` | First `civic observe assembly`, then `civic materialize assembly` | Two separately authorized effects; no combined runner |
| `civic-stage-assembly --publish-base-profile` | `civic publish assembly-profile` | `--database-url`; no fetch or filter flags |
| `civic-stage-assembly --resolve-review-item ID` | `civic review assembly-distinct-person --review-item-id ID` | `--resolution-note`, `--database-url`; current reviewed resolution also publishes the role Claim; CLAIM_PUBLICATION required |
| `civic-stage-gwanbo-personnel` | `civic observe gwanbo` | `--from-date`, `--to-date`, `--page-size`, `--resume`, `--database-url` |
| `civic-stage-legislative` default | `civic observe legislative-person` | `--name`, `--member-code`, `--age`, `--page-size`, `--max-pages` |
| `civic-stage-legislative --enumerate-bills` / `--resume` | `civic observe legislative` | `--age`, `--page-size`, `--max-pages`, `--resume`, `--database-url` |
| `civic-stage-legislative --publish-claims` | `civic publish legislative` | `--database-url`; no fetch flags |
| `civic-stage-local-election` default | `civic observe nec-page` | `--election-id`, `--type`, `--province`, `--district`, `--party`, `--page-no`, `--page-size` |
| `civic-stage-local-election --enumerate-candidates` | `civic observe nec-candidates` | `--election-id`, `--type`, `--page-no`, `--page-size`, `--resume`, `--database-url`; no filters |
| `civic-stage-local-election --enumerate-winners` / bare `--resume` | `civic observe nec-winners` | Same explicit winner scope flags; resume never selects the lane implicitly |
| `civic-stage-policy-research` | `civic observe policy-research` | `--title`, `--publisher`, `--publisher-code`, `--year-begin`, `--year-end`, `--page-no`, `--row-count` |
| `civic-stage-corporate-dart` default | `civic observe dart` | `--dataset`, `--corp-code`, `--business-year`, `--report-code` |
| `civic-stage-corporate-dart --enumerate` / `--resume` | `civic observe dart-executives` | `--business-year`, `--report-code`, `--listed-only`, `--resume`, `--database-url`; executive-status lane explicit |
| `civic-stage-mois-organizations` | `civic observe mois-organizations` | `--page-size`, `--max-pages`, `--resume`, `--database-url` |
| `civic-stage-public-institutions` | `civic observe alio-item4` | `--resume`, `--database-url`; current executive universe |
| `civic-stage-alio-money` | `civic observe alio-item12` | Repeatable `--institution-code`, `--resume`, `--database-url`; bounded known-positive default |
| `civic-import-alio-reviewed-claims` dry run | `civic inspect alio-item12` | `--organization-id`, `--institution-code`, `--earlier-fiscal-year`, `--later-fiscal-year`, `--database-url` |
| `civic-import-alio-reviewed-claims --commit` | `civic publish alio-item12` | Same reviewed inputs; verb and explicit effect replace `--commit` |
| `civic-materialize-alio-safe-people` dry run | `civic inspect alio-safe-people` | `--database-url` |
| `civic-materialize-alio-safe-people --commit` | `civic materialize alio-safe-people` | `--expected-receipt-sha256`, `--database-url` |
| `civic-materialize-nec-safe-people` dry run | `civic inspect nec-safe-people` | `--election-id`, `--types`, `--database-url` |
| `civic-materialize-nec-safe-people --commit` | `civic materialize nec-safe-people` | Same scope plus `--expected-receipt-sha256` |
| `civic-import-gukgam-reviewed-claim` dry run | `civic inspect gukgam-claim` | `--organization-id`, `--review-key`, `--database-url` |
| `civic-import-gukgam-reviewed-claim --commit` | `civic publish gukgam-claim` | Same exact reviewed inputs |
| `civic-preflight-gukgam-reviewed-claim-batch` | `civic inspect gukgam-batch` | `--manifest`, `--database-url` |
| `civic-import-gukgam-reviewed-claim-batch --commit` | `civic publish gukgam-batch` | `--manifest`, `--expected-manifest-sha256`, `--database-url` |
| `civic-preflight-orggo-reviewed-organizations` | `civic inspect orggo-organizations` | `--manifest`, `--proposal`, `--database-url` |
| `civic-import-orggo-reviewed-organizations --commit` | `civic materialize orggo-organizations` | `--manifest`, `--proposal`, `--expected-manifest-sha256`, `--database-url` |
| `civic-sync assembly-roster` | `civic observe assembly`, then `civic materialize assembly` | `--resume` belongs only to observe; not an acquisition-only alias |

`--enumerate`, `--enumerate-bills`, `--enumerate-candidates`, `--enumerate-winners`,
`--materialize`, `--publish-claims`, `--publish-base-profile`, and `--commit` are rejected
by the new CLI. Operation selection is always explicit in the command words.

ReviewedPersonBundle remains the existing manual/regression/exception API path. The
pinned baseline has no installed reviewed-Person bundle console script or JSON parser;
this CLI does not invent a duplicate importer or treat source-context preflights as
permission to import a reviewed bundle containing published Claims.

The explicit effect does not prove execution success. Each CLI receipt carries its
command and effect; failures carry a stable `COMMAND_FAILED` code without raw exception
or connection data. Tests use fake adapters and prove CLI boundaries only. Live source,
operational DB, materialization/publication, migrations, services and deployment require
separate approved execution and evidence.
