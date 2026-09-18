# Gukgam reviewed packet contract

## Purpose

The reviewed committee-site robots contract blocks repeated automated HTML/attachment collection.
Civic Intel still needs a safe way to turn a **finite, manually reviewed official plan document**
into deterministic structured metadata without treating the analyst or browser tool as the source
of truth.

This contract is the L1 parsing boundary for that path.

It is not a scraper, importer, Person materializer or publication bypass.

## Flow

```text
exact official National Assembly post/attachment
→ manual/Codex-assisted reading
→ field-by-field human review
→ fixed JSON packet
→ deterministic parser
→ typed schedule records
→ later provenance/import gate
```

The official National Assembly page remains the origin reference. The packet is an analyst
representation and never replaces the official source.

## V1 packet

The packet schema is:

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

## Fail-closed rules

The parser rejects:

- non-`*.na.go.kr` source URLs;
- mismatched `nttId` between packet and URL;
- weakened automated-access gate;
- unknown packet fields;
- duplicate schedule ordinals;
- duplicate target names inside a row;
- embedded witness/reference-person rows.

The parser does not fetch the source and does not create a Source, SourceSnapshot,
FeederObservation, Person, Organization, Claim or ClaimEvidence.

## Why import is deferred

The current canonical model correctly treats original source material and analyst-normalized
representations as distinct provenance. The reviewed-packet path still needs a narrow representable
lineage design before DB persistence: a local/private packet path cannot be invented as a fake
`Source.url`, and one metadata reference is not a validated provenance foreign key.

Therefore this slice deliberately stops at deterministic typed parsing.

The next import slice must reuse the existing canonical repository without adding a shadow raw store
or loosening SourcePolicy.

## Current real metadata fixture

The first metadata-only fixture pins the reviewed 2026 과학기술정보방송통신위원회 plan:

```text
nttId: 3078699
published: 2026-09-15
atchFileId: 7938f3a874d5441892124093d19da1df
fileSn: 2
filename: 2026년도 국정감사계획서.pdf
```

No schedule rows are asserted in that fixture yet. This prevents news summaries or unreviewed PDF
content from silently becoming canonical schedule data.
