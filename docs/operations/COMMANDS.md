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
separate source-specific operation. `civic inspect commands` inventories all 36 current routes.

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
