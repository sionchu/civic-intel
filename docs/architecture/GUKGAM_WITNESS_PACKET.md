# Gukgam witness packet and private review contract

This source-specific L1 implementation accepts a bounded, locally captured official committee
witness attachment. It reuses Source/Snapshot/Observation and adds no schema, raw payload store,
crawler, Person rule or publication path. The [source contract](GUKGAM_2026_SOURCE_CONTRACT.md)
and [collection roadmap](../operations/GUKGAM_COLLECTION_ROADMAP.md) govern its use.

## Literal fields

`GukgamWitnessRow` in `packages/domain/contracts.py` is strict and frozen. Its categories are
`INSTITUTION_WITNESS`, `GENERAL_WITNESS`, `REFERENCE_PERSON`. Unknown/private fields, actual
attendance fields, inferred institution dates and inconsistent source/name-cell locators fail closed.
Institution rows keep `printed_institution_group` and `printed_role`; group headings are list
context, not individual employment or canonical audit-target links. General/reference rows
separately keep `printed_affiliation_role` and `printed_audited_target`. Nullable source fields
remain absent. Requested/decision text is preserved without creating an event. One source name
cell may cover two role rows; rows/cells are not unique Persons or authoritative Person identifiers.

`gukgam-witness-packet.v1` has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | The literal schema above |
| `source` | Existing `ReviewedGukgamSource`: explicit committee, exact post/attachment IDs, rights mark and blocked automation gate |
| `attachment_url`, `attachment_sha256`, `page_count` | Credential-free same-host official locator, exact raw byte hash and page bound |
| `review_status` | `DRAFT_NOT_HUMAN_REVIEWED` or an actually supplied `HUMAN_REVIEWED` state |
| `selection` | `COMPLETE_ATTACHMENT` or `EXPLICIT_REVIEW_SUBSET`; neither establishes latest/national completeness |
| `rows` | Nonempty unique source-scoped rows, page/table/row and name-cell locators |

The research adapter verifies the 412 normalization hashes, category counts and 87 institution
heading/name-cell counts, then emits DRAFT packets. It cannot convert research into human review.
Human review is an operator-supplied factual attestation about the selected source fields.
The marker, CLI rights confirmation and agent review are not substitutes for that action;
even reviewed source fields provide no canonical identity or publication approval.

## Executable effects

From a checkout with the verified package installed:

```powershell
python -m apps.cli inspect gukgam-witness --allow-effect READ_ONLY --research docs/research/gukgam_2026_science_witness_linkage_2026-10-02.json
```

Research inspection opens no DB, checks no PDF bytes and fetches no source. Single-packet
inspection is `civic inspect gukgam-witness --allow-effect READ_ONLY --packet <packet.json>
--artifact <exact.pdf>`; it additionally verifies the actual local attachment bytes.

### Local DRAFT selection and literal corrections

The same single-packet inspect path can create a local operator edit template:

```powershell
civic inspect gukgam-witness --packet <draft.json> --artifact <exact.pdf> --write-draft-edits <edits.json>
civic inspect gukgam-witness --packet <same-draft.json> --artifact <same-exact.pdf> --draft-edits <edits.json> --draft-packet <selected-draft.json>
```

These are offline preparation commands with operational effect READ_ONLY. Their only write is
an explicitly requested new local operator file; no DB, source fetch, identity or publication
path opens. Existing output files and symlink targets are preserved by exclusive creation.
Research/multiple-source and plan inputs cannot be mixed with this preparation form.

The edit template has exactly `packet_hash`, `attachment_sha256` and `rows`. Each selected
row has `record_key`, `expected_row_hash` and `fields`. Remove a row entry to exclude it;
an empty selection fails closed. All hashes refer to the unmodified input. Literal corrections
are limited to `source_section`, `printed_name`, `printed_institution_group`, `printed_role`,
`printed_affiliation_role`, `printed_audited_target`, `requested_datetime_text` and
`decision_date_text`. Unchanged nulls remain null. Locators, ordinal, category, source/rights,
attachment and review state cannot be edited through this path. Row order follows the source.
The canonical parser revalidates every result, including shared name-cell consistency.

Preparation reuses the existing metadata-only SourcePolicy and accepts only the current exact
source decision's `KOGL_TYPE_1_VISIBLE_ON_EXACT_PARENT_POST` mark. This check does not establish
new rights or current amendment coverage. Exact local artifact proof is required. Already
HUMAN_REVIEWED input is rejected. The output always remains `DRAFT_NOT_HUMAN_REVIEWED` and
`EXPLICIT_REVIEW_SUBSET`, even when every input row was selected. It cannot prepare acquisition
without actual separate field review. Operator JSON retains permitted normalized fields locally;
stdout and errors contain only aggregate/hash information, never rows or correction values.
The template/output is not a SourceSnapshot, raw truth store, public DTO or human attestation.

### Source-to-plan review preparation

The existing inspect command also accepts repeated `--plan-packet <reviewed-plan.json>`.
It adds an offline `plan_linkage_review` using the existing plan parser and
`gukgam_review_key`; it opens no DB and performs no source retrieval. This is the independent
R3 preparation slice while actual R2 field review is pending, not identity materialization.

Matches use only an exact trimmed institution-list heading or printed audited-target label,
the explicit committee and source publication year. The printed plan audit year must also agree.
Affiliation/role and witness name never participate. Every matching plan occurrence is retained;
one match is still discovery only, and multiple matches require review. Requested/missing witness
dates stay literal; no plan date fills a field or establishes attendance. Missing labels and no
exact candidate are separate outcomes. No canonical UUID, identity or Claim is created.

Each candidate retains its plan packet hash and target occurrence key. Its `occurrence_ref_hash`
also binds the witness packet hash, raw witness SHA and witness row key. A bare plan review key
is version-insensitive and must not be used alone downstream. Duplicate attachment series fail
closed. Different posts may coexist as candidate inputs; current editions and supersession are
not established. Plan raw SHA is null and `artifact_bytes_verified=false`: the inspect join validates
the representation, not original plan bytes. Single-packet inspection separately checks witness
bytes; research inspection does not. Input review markers are not a new human attestation.

The private persisted witness review API is unchanged. This source-to-source report is local
operator preparation and must not become a public witness/target DTO or identity approval.

### Reviewed acquisition

After actual field review, exact rights review and the pinned sole-writer/backup/runtime
preflight, the acquisition form is `civic observe gukgam-witness --allow-effect SOURCE_INGESTION
--packet <reviewed.json> --artifact <exact.pdf> --confirm-exact-attachment-rights
--database-url <approved-target>`. Placeholders document required inputs; they are not an
approved live command or executed receipt. No mixed `--commit`, witness `materialize` or
witness `publish` command exists. Local artifact import needs no API key or network request.

The builder revalidates input and rejects DRAFT before any SourceRun/DB write. It reuses the
conservative committee attachment SourcePolicy: metadata permitted, automated fetch/fulltext/
AI/excerpts/commercialization disabled. Raw attachment SHA belongs to SourceSnapshot; reviewed
packet SHA and the exact row/hash manifest belong to SourceRun/Checkpoint. Identity hints are
empty. API/workers use the same UoW/session. Page commit is atomic; a failed page cannot advance
the checkpoint. Committed rows whose run did not finish SUCCESS stay unavailable for review.

## Version and private review

Checkpoint scope is `(publication year, explicit committee, nttId, atchFileId, fileSn)`.
Attachment series do not overwrite each other. Normalized observation hashes include raw
attachment SHA: byte-changed PDFs with unchanged literal fields create immutable observations
bound to the new snapshot; identical bytes/fields rerun without duplicates. Shared persistence
uniqueness and existing plan hashes are unchanged.

The review loader selects exactly the successful checkpoint's row/hash manifest, checks the
policy/source/snapshot chain and reconstructs the reviewed packet hash. A smaller explicit
review subset does not resurrect older unselected rows. Prior observations remain preserved.
Replacement/withdrawal relationships across different posts require review; current checkpoints
do not establish which post supersedes another. Plan v1 date ranges remain fail-closed for
Foreign Affairs; this witness implementation does not collapse them into single dates.

`GET /admin/gukgam/2026/witnesses` requires the existing review-surface opt-in. The private
operator factory retains local-host/token/origin gates, private/no-store and noindex headers.
Default/public API has no witness review route; acquisition-only Sources stay nonpublic.
The DTO contains literal rows and exact source/snapshot/observation references, with
`SOURCE_SCOPED_IDENTITY_REVIEW_REQUIRED` and `NOT_VERIFIED` attendance. Incoherent versions
return safe `SOURCE_VERSION_CONFLICT`. Public web transport routes remain unchanged.

## Witness-to-Person DRAFT Claim preparation

`civic inspect gukgam-witness-claim --database-url <existing-approved-db> --person-id <id>
--observation-id <id> --expected-observation-hash <sha256> --expected-packet-hash <sha256>`
is a READ_ONLY preflight. It prepares one in-memory canonical Claim/Evidence pair and emits
IDs, hashes, category and gate state only. It does not persist or export the pair and has no
observe/materialize/publish/review counterpart. SQLite requires an existing file and opens it
in URI read-only mode; PostgreSQL uses the existing coherent read-only transaction.

The existing witness checkpoint validation is shared by private review and Claim preparation.
The selected row must still belong to the current successful checkpoint's exact reviewed packet.
Caller-supplied observation and packet hashes must match. Old versions and rows removed by an
explicit subset are ineligible even when they retain historical identity links. Duplicate
observation versions or mismatched recovered contexts fail closed.

One application UoW verifies the existing current RESOLVED Person, unique active observation
binding and exactly one REVIEWED_LINK / REVIEWED_BRIDGE carrying a matching RESOLVED review.
The review must reference the same observation and Person, with an actual resolution timestamp
and nonblank note. Names, printed institution headings and nearby roles cannot supply this
authority. A shared name cell's second role row still needs its own exact reviewed bridge.
This preflight creates no such link or review. The generic automatic identity writer is unchanged;
the private reviewed admin path described below supplies a separate, explicitly confirmed link.

The predicate `LISTED_IN_GUKGAM_WITNESS_ATTACHMENT` means only an official source listing.
The pair remains DRAFT / CLAIM / `asserted_as_true=false`; it is not publication approval or
FACT conversion. Categories remain separate. Literal optional fields remain absent when null;
institution group headings do not become employment, target Organization IDs or planned dates.
Valid time is source publication, not requested attendance. Claim qualifiers bind exact packet,
raw attachment, observation and reviewed identity references; deterministic IDs separate source
versions, Persons, categories and role rows. Evidence keeps exact Source/Snapshot/Observation
and has no excerpt. Canonical evidence checks run while the publication gate remains closed.

This completes local R4 preparation only. Real witness field review, SSD acquisition, source-row
identity decisions, DRAFT persistence, publication and public UI/deployment remain separate steps.

## Private reviewed witness linking

The existing private `/admin/operations/preview` and `/commit` endpoints accept `LINK_PERSON`
for one witness observation from a current successful, HUMAN_REVIEWED 2026 checkpoint. The
existing immutable AdminCommand supplies its observation UUID, a current RESOLVED target
Person UUID, existing official ClaimEvidence UUIDs, explicit official career/biography continuity
basis, substantive reason and human review attestation. Source field review and identity review
are separate judgments. A name match, name cell, institution heading or attachment row key
cannot authorize a link. The metadata-only witness listing cannot be its own identity bridge.
The existing official cross-lane resolver and policy checks still govern selected bridge evidence.
Witness REGISTER_PERSON is rejected; this path creates no Person or Organization.

Preview writes nothing and uses the existing five-minute, actor/command-bound signed token.
The current source-series checkpoint, run, observation versions and Source/Snapshot/Policy,
current target and aliases, official bridge evidence/provenance and review/link state enter its
state fingerprint. Commit rebuilds under existing locks and needs explicit confirmation and
private write opt-in. Changed dependencies, superseded/excluded rows, invalid policy, ambiguous
identity and an already linked row fail closed. Validation is source-scoped; an unrelated
attachment cannot authorize the selected row. A scope exceeding 1,000 stored observation
versions fails the existing impact limit rather than weakening review.

One transaction persists the exact RESOLVED review, REVIEWED_LINK / REVIEWED_BRIDGE,
the existing canonical listing-only DRAFT Claim/Evidence and append-only operation receipt.
Review details retain the packet/observation hashes and bridge evidence IDs/basis. Source rows,
checkpoints and Persons remain unchanged. Evidence has no excerpt; requested attendance and
printed institution context remain literal. The read-only Claim inspector reconstructs that
same deterministic pair after an actual completed link. Exact request replay returns the
original receipt, and an insertion failure rolls back all domain writes and audit.

This implementation opens no witness publication or correction lane: those operations reject
the new listing predicate until its separate current-source release contract is implemented.
Actual source review/import, identity decisions, SSD writes, public UI and release still require
their operational work orders. Synthetic fixtures are not human attestations about real people.

## Evidence boundary

Offline tests cover real DRAFT 412 rows / the 47-row sample, missing dates, category separation,
merged roles, private/unknown field rejection, exact locators/hashes, DRAFT/effect gates,
metadata-only idempotent acquisition, changed-byte provenance, subsets, transaction rollback,
corrupt checkpoints and private/public API access. Synthetic HUMAN_REVIEWED fixtures attest to
no real source review or identity. SSD import, identities, Claim/Evidence publication, responsive
UI acceptance, Sites deployment and repeated/national collection remain separate unexecuted gates.
