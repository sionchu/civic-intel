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

## Evidence boundary

Offline tests cover real DRAFT 412 rows / the 47-row sample, missing dates, category separation,
merged roles, private/unknown field rejection, exact locators/hashes, DRAFT/effect gates,
metadata-only idempotent acquisition, changed-byte provenance, subsets, transaction rollback,
corrupt checkpoints and private/public API access. Synthetic HUMAN_REVIEWED fixtures attest to
no real source review or identity. SSD import, identities, Claim/Evidence publication, responsive
UI acceptance, Sites deployment and repeated/national collection remain separate unexecuted gates.
