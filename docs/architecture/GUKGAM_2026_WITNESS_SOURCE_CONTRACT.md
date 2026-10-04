# 2026 Gukgam witness-list source contract

## Status

`SOURCE-SPECIFIC / HUMAN-ASSISTED REVIEWED PACKET (v2) / AUTOMATED_COMMITTEE_HTML_BLOCKED / NO PUBLISHED REAL PACKET YET`

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

### Acquisition channels (packet v2)

`source.acquisition_channel` is one of:

- `OFFICIAL_SITE`: the operator saved the exact attachment from the committee homepage.
  `page_url` and `attachment_url` (official `https://*.na.go.kr`, same host), `artifact_filename`
  and `adoption_date` are required; `received_via`/`received_at` must be null.
- `OWNER_SUPPLIED_COPY`: the operator holds a copy whose official posting location is not yet
  known (for example a file handed over through a messenger). `page_url`/`attachment_url` may be
  null (a non-null value must still be an official URL). `artifact_sha256`, `received_via`
  (free text, e.g. "KakaoTalk TalkFile", no contact details) and `received_at` (ISO date) are
  required, and the list year must be fixed by `adoption_date` or `assumed_year`.

An owner-supplied copy is NOT an official source. It may be imported as
Source/SourceSnapshot/FeederObservation only after `HUMAN_REVIEWED`. Because `Source.url` is
mandatory and there is no migration, the Source carries the unfetchable placeholder
`https://owner-supplied-copy.invalid/gukgam-witness/{artifact_sha256}` (RFC 2606 reserved TLD)
under its own policy (`source_class = owner_supplied_reviewed_copy`, `can_fetch = false`, metadata
only). The snapshot metadata records `official_location = UNCONFIRMED`, `received_via`,
`received_at`. Moving to `OFFICIAL_SITE` later is a new reviewed packet version once the exact
official attachment is located and its bytes hash to the same sha256 (or a new version if they
differ).

The projection labels every such row "제공받은 사본 — 공식 게시 위치 확인 전"
(`provenance_label`), sets `source_url = null`, never exposes the placeholder URL or `received_via`,
and carries a limitation line stating that the official location is unconfirmed.

### Artifact formats and locators

`artifact_format` is `PDF`, `HWP` or `HWPX`. A locator is always
`{page_number, table_index, table_row}`. HWP/HWPX documents have no stable page numbers, so for
those formats `page_number` may be null provided `table_index` and `table_row` are present (both
always required). For `PDF` `page_number` is required. Locator tuples must be unique within a
packet. The projection shows `표 {table_index} {table_row}행` when there is no page number.

### Dates printed without a year

A row keeps the printed string verbatim in `attendance_date_text` (for example `10. 7.`); the
projection shows that text. A derived `attendance_date` (ISO) exists only when the date is
derivable: the text prints a year, or the packet declares
`source.assumed_year = {"year": 2026, "basis": "2026년도 국정감사 명단"}` (basis required). An
explicit `attendance_date` that disagrees with the text, or that cannot be derived from it, is
rejected. Without a declared year a year-less date stays text only. `assumed_year` must agree with
`adoption_date` when both are present, and `assumed_year.basis` is surfaced as
`attendance_year_basis` in the projection.

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

`{list_year}:{committee_name}:{list_version}:{row_number}` (never a name); `list_year` is the
`adoption_date` year, else the `assumed_year`. Document locator per row: artifact sha256 (plus the
official attachment URL when known), `page_number` (nullable for HWP/HWPX), `table_index`,
`table_row`. The packet may declare
`declared_totals` (증인/참고인 counts printed in the document); the parser rejects a mismatch.

## Fields

Allowed, as listed and verbatim: name; 소속/직위 (`affiliation_title`); 구분 증인|참고인
(`category`); the list's own section label (`list_section`, e.g. 일반증인/기관증인); 출석 일자 only
if printed (`attendance_date_text`, plus the derived `attendance_date` rule above);
`target_institution` only if the list states it explicitly; 신청 사유 only if printed
(`request_reason_text`, quoted verbatim, stored but not published).

신문요지 (the question summary some lists carry) stays stored-not-published: it is not a packet
field, is never copied to Claims or the projection, and this lane does not change that.

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
else stays unpublished.

No schema migration is made for a committee subject. Committee-level witness Claims attach to a
committee Organization only if one already exists. The importer looks one up (read-only, current
Organizations only, `claim_subject` in its report) and, when none exists, reports
`claim_subject_unavailable` and writes observation-only (Source/SourceSnapshot/FeederObservation).
It never creates an Organization. Creating the 17 standing-committee Organization records is an
owner decision outside this lane; until the owner decides, committee-level rows cannot become
Claims and are not projected.

## Pipeline (existing seams only, no migration)

reviewed packet (`gukgam-witness-reviewed-packet.v2`, `REVIEW_REQUIRED` → `HUMAN_REVIEWED`;
v1 is no longer accepted: it had no real packets)
→ `workers/gukgam_witness_import.py` (dry-run default; `--commit` writes Source/SourceSnapshot/
FeederObservation only, feeder `gukgam_reviewed_witness`)
→ Claim `LISTED_AS_GUKGAM_WITNESS_SOURCE_TEXT` built by
`packages/rendering/gukgam_witness_claim.py` and imported through the existing
`import_organization_claim` seam (a reviewed-claim worker is a follow-up; not part of this lane)
→ `GET /gukgam/2026/witnesses` projecting published Claims only.

## Open gates

- Real packets: a 교육위원회 draft exists outside git as an owner-supplied HWP copy
  (`REVIEW_REQUIRED`); it needs human review and, ideally, the official location.
- Committee Organization records (owner decision); until then `claim_subject_unavailable`.
- Where each committee posts the list (board) is unconfirmed.
- Version supersession semantics across list versions are not yet modeled in the projection.
- Reviewed-claim import worker.
