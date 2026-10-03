# 2026 Gukgam witness-list source contract

## Status

`SOURCE-SPECIFIC / HUMAN-ASSISTED REVIEWED PACKET / AUTOMATED_COMMITTEE_HTML_BLOCKED / NO REAL PACKET YET`

Companion to `GUKGAM_2026_SOURCE_CONTRACT.md`. This contract covers only the committee-adopted
"증인 등 출석요구의 건" lists (증인 and 참고인) for the 2026 National Assembly audit
(국정감사, starting 2026-10-06). It does not authorize a crawler.

## Authority

The only authoritative source is the list adopted by each standing committee and published on that
committee's own homepage (`*.na.go.kr`) as an attachment or 의결 document. The inventory is in
`docs/research/gukgam_2026_witness_source_inventory_2026-10-04.json`.

Not authoritative, discovery only: news and broadcast reports of adoption, press releases not
carrying the list, search results, member statements. A name seen only in such material is never
ingested. 열린국회정보 exposes no witness dataset.

## Access

On 2026-10-04 every reachable committee host (ports 443 and 444) returned
`User-agent: * / Disallow: / / Allow: /$`. Board, post and attachment paths are blocked for
automation. Therefore:

- no fetcher exists or may be added for these paths;
- an operator locates the exact attachment in a browser and saves the bytes locally;
- the importer takes those bytes, verifies the sha256 against the packet, and never fetches;
- anything not located is `MANUAL_DOWNLOAD_REQUIRED`, never "no witnesses".

## Rights

Reuse follows the mark printed on the exact post/attachment (e.g. 공공누리 Type 1). The mark is
recorded as `rights_mark` (null when none is stated; then the packet cannot claim a type). The
existing plan-lane policy applies: metadata storage only; full text, excerpts, AI processing and
raw republication stay disabled; source attribution required. Hence `request_reason_text` may be
stored in the observation but is **not** copied to Claims or the public projection.

## Bounded universe

2026 국정감사 witness/reference lists of the standing committees, per list version. A committee may
publish several versions (initial adoption, additions after adoption, 종합감사 additions). Each
version is a separate packet with its own `list_version`; a later version never silently replaces an
earlier one. Coverage is bounded and incomplete; absence of a row, a list or a committee is not
evidence that no person was requested.

## Stable record key

`{year}:{committee_name}:{list_version}:{row_number}` (never a name). Document locator per row:
attachment URL, attachment sha256, `page_number`, `table_index`, `table_row`. The packet may declare
`declared_totals` (증인/참고인 counts printed in the document); the parser rejects a mismatch.

## Fields

Allowed, as listed and verbatim: name; 소속/직위 (`affiliation_title`); 구분 증인|참고인
(`category`); the list's own section label (`list_section`, e.g. 일반증인/기관증인); 출석 일자 only
if printed; `target_institution` only if the list states it explicitly; 신청 사유 only if printed
(`request_reason_text`, quoted verbatim, stored but not published).

Forbidden: phone, email, addresses, 신청 의원 unless printed in the list, anything from news,
anything inferred. The parser has a closed field set and rejects email/phone-like text.

## Privacy

Many listed people are private individuals. They appear only as listed by the committee, with the
listed affiliation, and only after human review. Every projection states that a witness listing is
an attendance request, not an accusation, finding or evidence of wrongdoing, attendance or
testimony. Correction path: an owner-verified error is fixed by a new reviewed packet version and
Claim supersession; a takedown request is handled by withdrawing the Claim (publication status), and
the observation stays internal.

## Identity rule

Witnesses are NOT linked to canonical Person records. No name matching, no identity hints
(`identity_hints = {}`), no `PersonObservationLink`. The name is source-listed text, exactly like
ALIO executive names on organization pages ("현재 임원현황").

Attachment: rows attach to the committee Organization (scope `COMMITTEE`, Organization named exactly
the committee or "국회 {committee}"), or to an audited Organization only when the row's
`target_institution` states that Organization's exact name (scope `TARGET_INSTITUTION`). Anything
else stays unpublished. Creating the committee Organization record is an owner decision outside
this lane.

## Pipeline (existing seams only, no migration)

reviewed packet (`gukgam-witness-reviewed-packet.v1`, `REVIEW_REQUIRED` → `HUMAN_REVIEWED`)
→ `workers/gukgam_witness_import.py` (dry-run default; `--commit` writes Source/SourceSnapshot/
FeederObservation only, feeder `gukgam_reviewed_witness`)
→ Claim `LISTED_AS_GUKGAM_WITNESS_SOURCE_TEXT` built by
`packages/rendering/gukgam_witness_claim.py` and imported through the existing
`import_organization_claim` seam (a reviewed-claim worker is a follow-up; not part of this lane)
→ `GET /gukgam/2026/witnesses` projecting published Claims only.

## Open gates

- Real packets: none built; all committees `MANUAL_DOWNLOAD_REQUIRED`.
- Where each committee posts the list (board) is unconfirmed.
- Version supersession semantics across list versions are not yet modeled in the projection.
- Reviewed-claim import worker and committee Organization records.
