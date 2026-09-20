# Gukgam reviewed packet contract

## Purpose

The reviewed committee-site robots contract blocks repeated automated HTML/attachment collection.
Civic Intel still needs a safe way to turn a **finite, manually reviewed official plan document**
into deterministic structured metadata without treating the analyst or browser tool as the source
of truth.

The reviewed-packet lane is human-assisted and source-specific. It is not a scraper, Person
materializer or publication bypass.

## Flow

```text
exact official National Assembly post/attachment
→ one reviewed local copy of the exact attachment
→ raw attachment SHA-256
→ manual/Codex-assisted field extraction
→ field-by-field human review
→ fixed JSON packet
→ deterministic parser
→ Source / SourceSnapshot
→ FeederObservation
```

The official National Assembly attachment remains the source. The packet is an analyst-normalized
representation and never replaces the official artifact.

## V1 packet

The packet schema remains:

```text
gukgam-plan-reviewed-packet.v1
```

Source locator fields:

- explicit committee name;
- official detail URL;
- `nttId`;
- `atchFileId`;
- `fileSn`;
- attachment filename;
- publication date;
- visible rights mark;
- reviewed automated-access gate.

Schedule rows may contain only:

- ordinal;
- audit date;
- time text when explicitly printed;
- venue when explicitly printed;
- section/table heading;
- audited target names exactly as reviewed;
- source page number.

No witness/reference-person rows belong in a plan packet. They require a separate source record and
identity contract.

## Fail-closed parser rules

The parser rejects:

- non-`*.na.go.kr` source URLs;
- mismatched `nttId` between packet and URL;
- weakened automated-access gate;
- unknown packet fields;
- duplicate schedule ordinals;
- duplicate target names inside a row;
- embedded witness/reference-person rows.

## L2 canonical import boundary

The L2 importer requires four things in addition to a valid reviewed packet:

1. the exact local attachment bytes;
2. an exact official attachment URL on the same `*.na.go.kr` host;
3. matching `atchFileId` and `fileSn`;
4. explicit confirmation that the exact attachment's metadata reuse rights were reviewed.

The importer keeps original and normalized provenance separate:

```text
SourceSnapshot.content_hash
= SHA-256 of the exact raw attachment bytes

SourceRun.metadata.reviewed_packet_hash
= SHA-256 of the normalized reviewed JSON packet

FeederObservation.content_hash
= SHA-256 of one normalized schedule row
```

The reviewed packet hash is intentionally **not** stored as the SourceSnapshot content hash.

The SourceSnapshot stores no fulltext. The committee-site policy remains `can_fetch=False`
because repeated automated collection is blocked. Only reviewed metadata is persisted.

## Persistence scope

The first importer stops at:

```text
SourcePolicy
→ Source
→ SourceSnapshot
→ SourceRun / SourceCheckpoint
→ FeederObservation
```

It creates:

```text
0 Person
0 Organization
0 Claim
0 ClaimEvidence
0 identity links
```

Audited target names remain normalized strings in the reviewed observation. Later binding to a
canonical Organization requires an exact reviewed Organization identity contract; name equality is
not enough.

Dry-run is the default. A commit requires an explicit `--commit` and database URL.

## Version and rerun semantics

The official attachment SHA identifies the raw source capture. The packet hash records the reviewed
normalization version. A schedule row key is:

```text
nttId:atchFileId:fileSn:schedule:ordinal
```

Same key + same normalized row hash reuses the observation. A changed reviewed normalization creates
a new immutable observation version rather than overwriting the old row.

A new/replaced official attachment uses its own raw SHA and attachment locator. Correction/tombstone
semantics across separately published plans remain a later source-specific step.

## Current real metadata fixture

The first metadata-only fixture pins the reviewed 2026 과학기술정보방송통신위원회 plan:

```text
nttId: 3078699
published: 2026-09-15
atchFileId: 7938f3a874d5441892124093d19da1df
fileSn: 2
filename: 2026년도 국정감사계획서.pdf
```

That fixture still contains zero schedule rows, so it is **not import-eligible**. This prevents
unreviewed PDF content or news summaries from silently becoming canonical observations.

## Current reviewed packet set

The Science Committee packet plus six additional 2026 standing-committee plan packets have exact
official PDF hashes, field-reviewed schedule rows and successful importer dry-run receipts:

- 과학기술정보방송통신위원회;
- 국회운영위원회;
- 국방위원회;
- 행정안전위원회;
- 문화체육관광위원회;
- 농림축산식품해양수산위원회;
- 재정경제기획위원회.

The Foreign Affairs and Unification exact plan PDF is also captured, but its overseas audit rows
use multi-day ranges such as `10.11~10.22`. Packet v1 exposes only one `audit_date`, so that
committee remains fail-closed rather than collapsing a range to its start date.

## Review-only schedule projection

Imported plan observations may be rendered only on the internal review surface before
Organization binding and Claim/Evidence publication. The projection:

- is available only when the API review surface is explicitly enabled;
- selects rows from the checkpoint's current attachment SHA and chooses the latest immutable
  observation version for each provider record key;
- fails closed when the checkpoint row count and current observation set disagree;
- exposes reviewed schedule metadata and exact source provenance only;
- never emits a canonical Organization ID, Claim ID, run metadata, raw `normalized` payload or
  attachment fulltext.

The default public API does not expose this route, and `/gukgam/2026` remains unchanged until the
ordinary Claim/Evidence publication path can support the rendered facts.

A second internal-only projection may compare each source-scoped audited-target string with current
canonical Organization names using exact string equality only. An exact overlap is labeled
`EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY`; it is a review candidate, not a binding decision.
No-match and multiple-exact-match outcomes remain unresolved. This projection may expose candidate
Organization IDs/names to the operator, but it must not use aliases, fuzzy similarity, numeric
scores, rankings, embeddings or organizational proximity and must not create or update any
Organization, Claim, ClaimEvidence or identity link.

An operator may additionally run one review-only binding **preflight** by supplying:

- one exact current `review_key` for an audited-target occurrence;
- one existing current canonical Organization ID.

The preflight re-runs the exact-name candidate projection, requires exactly one current candidate,
requires that candidate ID to equal the operator-supplied Organization ID, and recovers the exact
committee-plan source provenance for that occurrence. Its receipt is always `DRY_RUN` with
`binding_committed=false` and `claim_publication=false`. An unknown occurrence, no exact
candidate, multiple candidates, a wrong/superseded Organization ID, or non-unique provenance fails
closed. The route remains internal-only and performs no persistence write.

## Next source step

Continue exact-attachment acquisition for the remaining standing committees and use v1 only where
the source schedule is losslessly representable. Do not introduce a parallel packet schema merely
for one blocked source; if date ranges recur across official plans, extend the canonical contract in
place with deterministic regression coverage before importing them.
