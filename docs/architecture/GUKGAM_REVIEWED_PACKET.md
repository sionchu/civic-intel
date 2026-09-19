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

## Next source step

Obtain one exact reviewed local copy of the pinned Science Committee PDF, record its official
attachment URL and raw SHA-256, complete the schedule rows field-by-field, then run the importer in
dry-run mode. Only after the dry-run receipt is independently checked should the single reviewed
packet be committed.
