# National Assembly asset disclosure source gate

## PETI public factual totals — 2026-10-09: LOCAL_STAGED

The official PETI public search (`https://www.peti.go.kr/peOptpListVie.do`) opens a
public HTML detail route (`https://www.peti.go.kr/peoptp/openPeOptpListVieDtlPop.do`).
Bounded Aside review found one selected National Assembly record and verified the
printed total columns: 종전가액(천원), 증가액(실거래가격), 감소액(실거래가격),
현재가액(천원). This is a public declared total, not personal self-only or market
wealth. The inspected report-type label was unavailable and remains UNKNOWN.

Public factual metadata is assessed separately from PDF/media redistribution:
[Public Service Ethics Act Article 10](https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1024570355)
and [Copyright Act Article 7](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0007&lsiSeq=283335&urlMode=lsScJoRltInfoR)
provide the reviewed public-disclosure/legal basis. No blanket PDF/photo reuse
licence or individual consent requirement is inferred for these factual fields.
The Assembly Gazette robots, AI and human-transcription constraints below remain
specific to that separate source route.

`build_peti_asset_capture` in the existing asset importer takes an explicit supplied
SourcePolicy before reading fields. It requires STORE_METADATA, the PETI domain,
BROWSER provenance, disabled FETCH, no fulltext storage and no excerpt display.
FETCH is transport-neutral: this function is supplied-receipt staging, not a browser
or HTTP collector. It does not create a policy, infer a commercial-use restriction,
assert a copyright licence, fetch a page, or write to a database.

The closed receipt permits only exact public routes, disclosure/registration dates,
National Assembly institution/office, printed public name, verified total column
labels, exact transport-safe integer amounts in THOUSAND_KRW, an explicitly visible
report label or UNKNOWN, and PRINTED_PUBLIC_DISCLOSURE_TOTAL_NOT_SELF_ONLY scope.
Prior + increase - decrease must equal current. A printed zero or signed total is
preserved; absence is never zero. Raw DOM/body/PDF, session-bearing URLs, family
rows, addresses, asset items and HUMAN_REVIEWED flags are prohibited fields.

The canonical Source is the public detail route, reused across records to preserve
unique Source URLs; its route publication time is unknown. SourceSnapshot stores
only the sanitized receipt and its deterministic metadata hash. FeederObservation
uses `peti_public_declared_total`, references that exact snapshot, and retains the
same allowed normalized fields. Record disclosure date is metadata, not an invented
Source publication timestamp. No second raw store or table is introduced.

The deterministic record key hashes disclosure date, registration date, institution,
office and printed name. It is a public selector locator, **not** an authoritative
Person identifier. Observation identity hints remain empty. Names or a single search
match cannot authorize automatic creation, linkage or merge.

`build_peti_asset_total_claim` requires a supplied current resolved canonical Person,
an exact existing active REVIEWED_LINK and its resolved review. It never manufactures
a reviewer/link or merges Persons, and defaults the returned Claim to DRAFT. The
existing asset reader dispatches `peti_public_declared_total_metadata_v1` through the
same publication gate and Evidence/Source/Policy lineage; exact Claim text, integer
amounts, unknown report type, snapshot metadata hashes and reviewed linkage are
checked. A different immutable sibling version blocks output until explicit review.

This milestone is local staging and deterministic fixture verification. No canonical
PETI policy/record/link was written, no real PETI Claim was published, and no operational
asset coverage or deployed service result is claimed. Sanitized source-review evidence
is in `dist/full-goal-evidence/followup/readiness/peti-headline-review.json`.

## Decision — 2026-10-05: L1 CONTRACT_STAGED (human-assisted Gazette packet path)

**L1 CONTRACT_STAGED; human-assisted reviewed-packet path; no real packet imported yet.**
The owner directed implementation. The 2026-09-12 blockers (release coverage, revision/key
semantics, permitted automated route) are **not** resolved and were not guessed past; the lane
implements only the narrowest safe path the gate already allowed: one rights-reviewed official
Gazette issue, transcribed by a human, imported as metadata-only source observations. No L2 is
claimed: L2 needs a real rights-approved packet imported end to end. No automated enumeration,
scheduler, OpenWatch/opengirok ingestion, Person link, AssetDisclosure row or Claim exists.

### Authority and route

- **Authority:** the official 국회공보 재산변동사항/재산등록사항 공개 issue published by
  국회공직자윤리위원회, as listed in the official Gazette index on `www.assembly.go.kr`
  (`/portal/cnts/cntsNamgzn/gongbo.do?cntsDivCd=NAMGZN&pdfClsCd=CPR&menuNo=601019`) with
  per-issue detail pages `/portal/cnts/cntsCont/dataA.do?cntsDivCd=NAMGZN&...&pdfId=<n>`
  (e.g. 2025-51 `pdfId=379578`, browser-observed on 2026-09-12 above).
- **robots.txt re-observed 2026-10-05:** `User-agent: * / Disallow: / / Allow: /$`; an automated
  fetch tool also refused the host on robots grounds. Therefore nothing in this lane fetches
  from `www.assembly.go.kr`; the index/detail locations above were not re-crawled. A human
  operator opens the detail page in a normal browser and saves the exact PDF.
- OpenWatch / opengirok / 정보공개센터 sheets remain **discovery and methodology references only**;
  they are never an authority, never imported, and never a source of MONA_CD.

### Pipeline (existing seams only, no migration)

```text
operator saves exact Gazette PDF (browser)            -> local file, never committed
reviewed packet `assembly-asset-gazette-reviewed-packet.v1` (REVIEW_REQUIRED -> HUMAN_REVIEWED)
  -> packages/connectors/assembly_asset_packet.py      (closed-schema validation, no I/O)
  -> packages/verification/assembly_asset_import.py    (HUMAN_REVIEWED gate, %PDF + sha256
                                                        match, SourcePolicy gate)
  -> workers/assembly_asset_import.py                  (dry-run default; --commit writes
     Source / SourceSnapshot / FeederObservation only via commit_source_page;
     feeder `assembly_asset_gazette_reviewed`)
```

The worker requires `--confirm-gazette-rights-review` (owner attests the issue's reuse rights
were reviewed) and, with `--commit`, `--database-url`. It never downloads anything.

- **SourcePolicy** (`gazette_asset_policy`, domain `www.assembly.go.kr`): `can_fetch=False`,
  metadata only; no fulltext, AI, excerpt or commercialization; `robots_checked_at=2026-10-05`.
  Before commit the worker loads stored policies: a stored decision for the domain wins and must
  permit `STORE_METADATA` and deny fetch; a different policy id bound to the domain, a BLOCKED
  mode or denied metadata storage refuses the import with nothing written. Because SourcePolicy is
  unique per domain, any later lane on `www.assembly.go.kr` must reuse or deliberately revise
  this policy rather than add a conflicting one.
- **Source** URL is the canonical official detail URL rebuilt from the packet's `pdf_id` (the
  packet `page_url` must be that exact host/path with matching `cntsDivCd=NAMGZN`/`pdfId`);
  `published_at` is the printed Gazette date (KST).
- **SourceSnapshot**: `content_hash` = raw PDF sha256; metadata carries issue, title, date,
  disclosure kind, pdf_id, filename, rights mark, capture mode, unit and value semantics;
  `fulltext=None`. The PDF bytes are not stored (no second raw store).

### Packet contract

Source block: `gazette_issue` (`YYYY-N`, year must equal `publication_date`), `gazette_title`,
`publication_date`, `disclosure_kind` (`정기` | `수시`), `reporting_period_text` (verbatim) with
optional ISO start/end (end ≤ publication date), `pdf_id`, `page_url`, `artifact_filename`,
`artifact_sha256`, `rights_mark`, `automation_gate = ASSEMBLY_GAZETTE_AUTOMATION_BLOCKED_ROBOTS`.
Packet-level `coverage` (`SELECTED_MEMBERS` | `FULL_ISSUE`) and `declared_member_count` are
persisted in run metadata so a partial packet is never mistaken for a complete issue.

Member block: `printed_member_name`, `printed_affiliation`, `printed_position` (must be exactly
`국회의원`: member-level only; other high officials in the same issue are rejected),
`report_type` (`변동신고` | `최초등록` | `재등록` | `퇴직`; a `정기` issue accepts only `변동신고`;
registration types carry only `current_value`), optional `reviewer_stated_mona_cd` +
`mona_cd_basis` (both or neither), `total_locator`, `declared_totals`, `items`.

Item block: exact `locator {page_number, table_index, table_row}`, `holder_relation` (coarse
code SELF | SPOUSE | LINEAL_ASCENDANT | LINEAL_DESCENDANT | OTHER_REPORTED_RELATIVE; the printed
kinship term is not kept), `item_category` (statutory 재산의 구분 as a closed code set, incl.
DEBT), optional verbatim `item_category_text`, optional short `item_kind` (재산의 종류, e.g.
대지/아파트/예금), optional `region_sido`, and amounts `prior_value`, `increase`, `decrease`,
`current_value`, each `{text, value}`: printed thousand-KRW text plus parsed integer, which must
agree (`-`/`△` negative allowed; parentheses such as 실거래가격 notes are rejected). A missing
amount is `null`, distinct from a printed `0`.

Validation fails closed on: unknown fields anywhere (so `location`, `account_number`,
`change_reason`, family names etc. cannot be supplied); contact-, address- (번지/동·호/로·길+number,
지번 `12-3`, ㎡, 시/도+시/군/구) or account-like (`NNNN-NN-NNNNNN`, ≥10 digits) text in permitted
text fields; a region outside the closed 시/도 list; duplicate locators or MONA_CDs; amount
text/value disagreement; and a **declared-total mismatch**: for each member, printed
`prior_value` and `current_value` totals must equal the item sum with DEBT items subtracted.

### Privacy decisions (AGENTS.md)

- **Location:** `소재지 면적 등 권리의 명세` is never accepted. The only location kept is
  `region_sido` from a closed list of 17 시/도 plus `해외`. 시/군/구 was rejected for now: with
  item kind (e.g. 아파트) it narrows a residence more than the coarse public-interest signal
  needs, and the closed list makes address leakage structurally impossible. Widening it is an
  owner decision.
- **Relative-held items: excluded.** The existing AssetDisclosure/AssetItem contracts do not
  model a relation category, so the lane prefers exclusion. Relative-held rows may appear in the
  packet only as relation code + category + amounts (no text, kind or region) so the printed
  member totals can be cross-checked; they are dropped before persistence. Observations carry
  only `relative_items_policy = RELATIVE_HELD_ITEMS_EXCLUDED_FROM_OBSERVATIONS`; the run metadata
  keeps only an aggregate excluded-row count. The persisted member total is the printed headline
  figure and is labeled `PRINTED_MEMBER_TOTAL_INCLUDES_REPORTED_RELATIVES`.
- **Change reasons (변동사유):** not accepted. The 2026-09-12 minimal design found free-text
  reasons unnecessary and they can name relatives or transactions; enabling them is an owner
  decision.
- No family names, account/parcel numbers, contacts or 고지거부 annotations are modeled.
  고지거부 and similar non-disclosure markers stay outside the contract (an absent row is
  unresolved, never "no assets").

### Identity

No Person is created, merged or linked. `identity_hints` is `{}` unless the reviewer states an
official MONA_CD with its basis; then it is
`{assembly_mona_cd_stated, identity_basis: PACKET_REVIEWER_STATED, link_mode:
REVIEW_ONLY_NO_AUTO_LINK}`. The Gazette itself does not print MONA_CD, so a stated code is a
reviewer assertion awaiting an exact-code linkage review, never automatic authority. Printed
name + issue + locator remain review-only handles. Observations deliberately omit
`canonical_name`, so the generic `materialize_feeder_observation` path refuses them (tested).

### Observations, keys and values

Per member: one `MEMBER_DECLARED_TOTAL` observation; per self-held item: one
`SELF_HELD_ASSET_ITEM` observation referencing the member's record key. Scope key
`gazette:<issue>:pdf:<pdf_id>`; provider record key `<issue>:p<page>:t<table>:r<row>` — a
**snapshot-scoped observation key**, never a Person or a durable real-world asset identity.
Every observation carries `authority = OFFICIAL_NATIONAL_ASSEMBLY_GAZETTE`,
`amount_unit = THOUSAND_KRW` and **`value_semantics = DECLARED_VALUE_NOT_MARKET_WEALTH`**:
these are values declared under the Public Service Ethics Act as printed in the Gazette, not
market wealth, not independently verified and not a wrongdoing signal.

Re-importing the same packet is idempotent (observations unchanged). A corrected packet that
changes a row appends a new observation under the same record key; nothing is overwritten and no
precedence is chosen (see open decisions).

### Tests

`tests/test_assembly_asset_disclosure.py` with a clearly synthetic fixture
(`tests/fixtures/assembly_asset_synthetic_reviewed_packet.json`, issue `2099-1`, `pdfId=0`):
packet validation, forbidden fields and address/account-like text, total mismatch, registration
shape, amount parsing, HUMAN_REVIEWED/PDF/sha256 gates, relative-item exclusion, dry-run writes
nothing, commit idempotency, corrected-packet append, no Person/PersonObservationLink/
AssetDisclosure/AssetItem/Claim rows, materializer refusal, and stored-policy denial.

### Still-open owner decisions

1. **Rights/route:** confirm reuse terms for each specific Gazette issue (Copyright Act Art. 7
   classification, attribution, redistribution) before passing `--confirm-gazette-rights-review`;
   the automated route stays blocked by robots.txt.
2. **Which issues to cover** first (e.g. 2026-54 정기, 2024-107 수시) and whether packets may be
   `SELECTED_MEMBERS` or must be `FULL_ISSUE`.
3. **Revision semantics:** precedence between a corrected packet and an earlier one for the same
   locator, Gazette correction/republication handling, and cross-release item continuity.
4. **Cross-check rule confirmation:** the net (assets − debts) prior/current total rule and the
   statutory category code list are UNVERIFIED against a real Gazette PDF; the first real packet
   must confirm or correct them. Increase/decrease totals are stored verbatim but not
   cross-checked until the Gazette's netting of debt changes is confirmed.
5. **Optional fields:** whether 시/군/구, change reasons or a relation-category aggregate may ever
   be stored, and whether real-transaction-price columns should be modeled.
6. **Identity/publication:** an exact MONA_CD linkage review path and any Claim/AssetDisclosure
   materialization (requires a Person link, so it remains out of scope here).

The L3 blocking conditions below remain in force.

## Decision — 2026-09-12 (historical)

**L0 RESEARCHED; BLOCKED. No L1/L2/L3 promotion.** Research and aggregate QA are
complete; no runtime connector, persisted observations, Person links or migration were added.
Existing asset-shaped domain classes are not a staged source-specific contract or fixture.
The seven existing L3 feeders remain unchanged. Employment review remains
L1 CONTRACT_STAGED with L3 promotion blocked; CleanEye remains L0 RESEARCHED; BLOCKED.

OpenWatch is a curated secondary structured source, not one canonical feeder and not an
authority for Person creation. This gate is limited to National Assembly asset disclosures.
Other datasets require independent scope, origin, policy, identity and completeness decisions.

## Evidence inventory and access observations

- [OpenWatch dataset directory](https://www.openwatch.kr/dataset): current browser-rendered
  download manifest and CC BY-SA 4.0 statement.
- [Asset documentation](https://docs.openwatch.kr/data/national-assembly/asset-disclosure):
  amounts in thousand KRW; National Assembly Gazette PDFs transcribed by 정보공개센터 into
  Google Sheets, then incorporated by OpenWatch.
- [Member documentation](https://docs.openwatch.kr/data/national-assembly):
  18th–22nd Assembly; upstream Assembly codes and 헌정회 codes.
- [Assets API documentation](https://docs.openwatch.kr/api-1/national-assembly/assets) and
  [members API documentation](https://docs.openwatch.kr/api-1/national-assembly/members):
  linked Swagger 1.1.0 inspected. Its SwaggerHub mock server was not used as evidence.
- [opengirok catalog at inspected revision](https://github.com/opengirok/congress_asset_disclosure/tree/a03999074636191dfe86d299567b918fd85cf14a):
  README only, latest commit dated 2025-09-24; six catalog commits inspected.
- [2025 official Gazette detail](https://www.assembly.go.kr/portal/cnts/cntsCont/dataA.do?cntsDivCd=NAMGZN&menuNo=601019&pdfClsCd=CPR&pdfId=379578):
  normal browser displays 제2025-51호(정기재산공개), 2025-03-27, PDF viewer/download.
- [Official Gazette index](https://www.assembly.go.kr/portal/cnts/cntsNamgzn/gongbo.do?cntsDivCd=NAMGZN&pdfClsCd=CPR&menuNo=601019):
  a browser title search for `재산` returned 61 matching publications across 7 pages; the
  unfiltered catalog showed 4,640 publications across 464 pages. Results expose publication
  title/date plus preview/download controls, including 2026-54 (2026-03-26), 2025-51
  (2025-03-27), 2024-107 (2024-08-29) and 2024-36 (2024-03-28).
- [Assembly robots](https://www.assembly.go.kr/robots.txt): observed
  `User-agent: * / Disallow: / / Allow: /$`. No repeated origin enumeration was attempted
  after observing this restriction.

Plain HTTP requests to the documented OpenWatch assets and members API returned 403 HTML
security-checkpoint responses, not JSON and not empty datasets. Ordinary browser navigation
completed the site's challenge and exposed the public dataset page/download redirects.
The Google Sheets XLSX exports were readable. Thus public bulk research access exists, but a
reviewed machine API contract has not been demonstrated. Search-tool failures on Assembly
detail URLs likewise do not mean the normal browser cannot open them.
No Firecrawl, generic crawler, authentication bypass or runtime dependency was introduced.

## Universe, releases and annual completeness

OpenWatch's current directory labels March 2016–2026 (eleven regular releases) plus August
2016, 2020 and 2024 (fourteen labels). Its asset documentation stops at March 2025 and mentions
only August 2016/2020. opengirok's pinned catalog has thirteen sheets: March 2016–2025 and
the three August releases. OpenWatch's 2024 August label points to
`/api/download/national-assembly/assets-2024-03`, the same URL as March 2024.
No guessed August endpoint was substituted. opengirok has a separate August 2024 sheet.

The source sheets cover Assembly high public officials, not exclusively elected MPs.
Annual populations must not be compared to a fixed 300-seat denominator. Regular filing,
new registration, reregistration and retirement are distinct publication types; a filing
period, valuation/as-of date and publication date are not interchangeable.

The official catalog revalidation establishes a page-based publication index and confirms
publication-level origin candidates for the 2026 March and recent curated releases. It does
not reconcile each curated row to a Gazette page/item, establish a correction or republication
chain, or turn the publication count into a complete asset-disclosure universe.

| Release | Gazette date / issue as cataloged | opengirok named detail rows | Diagnostic name-role groups | Duplicate excess excluding ordinal |
|---|---|---:|---:|---:|
| 2016-03 | 2016-03-25 / 2016-23 | 6,422 | 328 | 6 |
| 2016-08 | 2016-08-26 / 2016-78 | 2,779 | 154 | 17 |
| 2017-03 | 2017-03-23 / 2017-36 | 6,742 | 336 | 25 |
| 2018-03 | 2018-03-29 / 2018-41 | 6,591 | 324 | 27 |
| 2019-03 | 2019-03-28 / 2019-31 | 6,707 | 330 | 24 |
| 2020-03 | 2020-03-26 / 2020-36 | 6,527 | 323 | 12 |
| 2020-08 | 2020-08-28 / 2020-98 | 6,348 | 332 | 34 |
| 2021-03 | 2021-03-25 / 2021-42 | 6,168 | 335 | 23 |
| 2022-03 | 2022-03-31 / 2022-31 | 5,839 | 326 | 3 |
| 2023-03 | 2023-03-31 / 2023-54 | 5,971 | 333 | 4 |
| 2024-03 | 2024-03-28 / 2024-36 | 5,749 | 323 | 1 |
| 2024-08 | 2024-08-29 / 2024-107 | 5,160 | 290 | 11 |
| 2025-03 | 2025-03-27 / 2025-51 | 6,416 | 335 | 13 |

The dates/issues above are catalog provenance, not independently reconciled original PDFs.
Every year's **origin-relative completeness remains unproven**. The older eight entries have
textual Gazette citations rather than direct origin links. Later links identify 2022
`nttId=1707818`, 2023 `nttId=2184625`, 2024 March `pdfId=379354`, August
`pdfId=379431`, and 2025 March `pdfId=379578`. The official index now lists 2026 March as
`국회공보 제2026-54호(정기재산공개)` dated 2026-03-26, but the exact origin artifact
identifier and row-level reconciliation are still absent from the release manifest.
The 2016 March catalog's descriptive new-member wording conflicts with its regular-release
label; do not infer a type from that prose.

August 2020 detail tabs contain new 2,509 / reregistered 376 / retired 3,463 rows.
August 2024 has new 2,443 / reregistered 276 / retired 2,441.
These counts include relative-owned assets and disclosure markers. They are not counts of
assets, unique Persons or provider-identified disclosures. Subtotals and summary tabs must
not be added to detail counts. Diagnostic grouping by name/role is not identity resolution.

## Read-only structured QA

[Aggregate evidence](../research/assembly_asset_qa_2026-09-12.json) records timestamps,
source URLs, capture hashes, per-tab fields, row counts, missingness and duplicate counts.
[Finite QA script](../research/assembly_asset_qa.py) reads explicitly listed public workbooks
in memory with a preinstalled analysis runtime. It neither imports Civic Intel nor writes
to its database; no raw workbook, personal row, address or contact values were retained.
The final pass covers thirteen opengirok workbooks, three recent OpenWatch asset workbooks,
and the OpenWatch member workbook. It does not inspect every historical OpenWatch export.

| OpenWatch regular release | Named detail rows | Summary rows | Exact code-linked rows / detail rows | Distinct codes |
|---|---:|---:|---:|---:|
| 2024-03 | 5,749 | 323 | 5,185 / 5,749 (90.19%) | 291 |
| 2025-03 | 6,416 | 335 | 5,832 / 6,416 (90.90%) | 299 |
| 2026-03 | 6,127 | 330 | 5,442 / 6,127 (88.82%) | 287 |

All nonblank `monaCode` values in those three sheets occur in the OpenWatch member workbook.
This is internal crosswalk membership, **not** validated linkage to existing Civic Intel Persons.
Blank-code rows are 564/584/685; the separate count of rows lacking MP role markers is
also 564/584/685. Equal counts alone do not prove that these are exactly the same rows.
Summary rows without codes are 32/36/43. They must not become new Person candidates.

The member workbook has 1,609 term-associated rows, 1,000 distinct nonblank `monaCode` values,
839 distinct nonblank `hjId` values and 329 rows missing `hjId`. No code maps to multiple
nonblank `hjId` values in this capture. This does not prove upstream accuracy or completeness.

Full-row duplicate excess is zero in regular-year sheets because ordinals distinguish rows.
Excluding `NO/No` gives the table above; recent OpenWatch detail duplicate excess is 1/13/16
(about 0.017%/0.203%/0.261%). August exact duplicate excess is 17/34/11
(about 0.612%/0.536%/0.213%). Equal contents can represent legitimate separate items:
neither deduplicate nor merge automatically.

Missingness preserves numeric zero as present. opengirok regular current-value blanks:
2016 250; 2017 202; 2018 223; 2019 0; 2020 265; 2021–2025 0.
New-registration tabs use different valuation headings, so an absent `현재가액` column
is not a missing-cell count. Recent OpenWatch current-value blanks are zero, but
real-transaction subfields and change reasons have many blanks. A blank, zero, refusal,
not-applicable and undisclosed value must remain different states.

All seventeen XLSX byte hashes changed on repeat export while named-row counts stayed equal.
For an immediate repeated 2026 capture, ordered named-row content hashes excluding ordinal
were equal in both tabs. Export-byte churn therefore cannot be called a correction.
Only that 2026 content repeat was compared; no historical row revision rate was established.
Git catalog commits do not version mutable Google Sheet contents.

## IDs, API and correction semantics

- `monaCode` is documented as the Assembly member code. The canonical local namespace is
  `assembly_mona_cd`, populated from official `MONA_CD`. Prefer that official anchor.
- `hjId` is a 헌정회 provider code, not an interchangeable MONA_CD.
- OpenWatch API Member `id` is a provider/crosswalk identifier. Its example resembles an
  Assembly code, but its schema does not establish a distinct `monaCode` field or prove
  equality. Never infer that equality from formatting.
- opengirok sheets inspected contain ordinals and name/role fields, not official member
  IDs. No name-only bridge to OpenWatch or Civic Intel is allowed.
- Member API documents `page` and `pageSize` (10–100) with total count, but its term
  description says 17th–21st, unlike the 18th–22nd dataset documentation.
- Asset API documents date/type/relation/kind/detail filters and a total count, but no
  asset page/page-size contract. Asset schema has integer `id` and amount fields, not
  a documented disclosure ID, member FK, origin Gazette/page, date or revision field.
  Preserve literal schema spellings such as `currentValutaion` when evaluating it;
  do not manufacture fields or a complete paginated response.
- XLSX exports provide whole workbooks, but no immutable release manifest/checksum,
  contractual request pacing or typed reconciliation with Gazette contents was established.
- No stable disclosure-level ID, cross-release item ID, amendment link, deletion/tombstone
  rule or republication precedence was established. Row ordinals and API integers alone
  do not supply those semantics. New/reregistered/retired are not correction types.
- The official Gazette index's pagination and attachment links identify publication artifacts,
  not disclosure or item versions. The revalidation observed no correction, amendment,
  replacement or republication semantics in the catalog contract.

A justified source-derived snapshot-scoped observation key is allowed by the batch architecture;
a provider-generated permanent ID is not universally mandatory. Here no validated reconciliation
rule yet tells a corrected row from a new disclosure/item. A future immutable release + tab +
ordinal can identify an observation, never a Person or an unchanged real-world asset. Content
hash alone would also collapse repeated legitimate equal-valued rows.

## Rights and storage gate

[OpenWatch policy](https://docs.openwatch.kr/about) and the live directory license data under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). It permits sharing and adaptation,
including commercial use, with attribution, license reference, change indication and applicable
ShareAlike obligations for adaptations. It does not grant privacy/publicity rights or relicense
third-party material. Data licensing must remain separate from Civic Intel's Apache-licensed code;
this is not a conclusion that all application code must become BY-SA.

opengirok's README expressly allows free use of the cleaned data with 정보공개센터 attribution.
Its inspected tree has no LICENSE file or processing code. This is a positive prose data-use
statement, not an Apache/MIT code grant or a documented automated-access/version contract.
Do not import a license from an unrelated opengirok repository. No OpenWatch code repository or
code license was located in the checked official docs/directory; no provider code is being reused.

The Assembly portal's copyright-policy modal distinguishes owned/publicly usable works,
KOGL type-1 marked works and unmarked material requiring consultation. See the policy modal on
[this official portal page](https://assembly.go.kr/portal/bbs/B0000051/view.do?nttId=3869667).
The inspected Gazette detail had no item-specific KOGL grant. However,
[Copyright Act Article 7](https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1029423769)
excludes official notices and similar government works from protection. Absence of a KOGL mark
is therefore **not proof that Gazette facts/notices cannot be reused**. Classification of the
specific publication, third-party/curation rights, privacy and automated route permission are
separate questions. Technical availability alone does not set SourcePolicy permissions.

Before production, record a policy for each origin/curator layer covering normalized storage,
redistribution/attribution, commercial use, excerpt/AI use and an allowed bounded access route.
No blanket fulltext or AI-use permission is inferred. Existing NOTICE already preserves external
data rights; no external dataset is committed or relicensed in this milestone.

## Actual domain model and smallest possible design

Repository inspection found existing canonical `AssetDisclosure` and `AssetItem` in
`packages/domain/contracts.py`. AssetDisclosure has person_id, source_id, items and temporal
fields; AssetItem has description, optional float value/currency/claim_id. SQLAlchemy
`AssetDisclosureRow` and `AssetItemRow` already exist in `packages/domain/db.py` and the
initial Alembic schema. This is not a missing-model project.

The shared repository currently has no asset mapper/materializer, and
`GET /people/{person_id}/assets` returns an empty list after checking the person.
Domain tests cover table presence, not a live asset ingestion workflow. Existing classes
do not encode a reviewed disclosure-type, period, item-key or amendment contract.
No new model, shadow schema or migration is warranted by this blocked gate.

For a later staged slice, reuse Claim qualifiers/temporal semantics and minimal
FeederObservation fields to represent “the specified release reports this declared amount,”
not true market wealth. Explicitly distinguish declaration period, valuation date, publication
date, capture time and correction state; never substitute TemporalRecord's default now.
Preserve amount units and exact integer/decimal representation rather than adding financial
calculations through AssetItem's float. Debt, prior value, current value and real-transaction
amount are not interchangeable. A persistent extension is proposed only if tested semantics
cannot be expressed faithfully by the existing contracts; it requires a reversible migration
and the shared repository, not another financial framework.

Required provenance stays three-layered:

```text
National Assembly Gazette Source + origin SourcePolicy / SourceSnapshot
  -> opengirok and/or OpenWatch distinct transformation Sources + their policies/snapshots
  -> Civic Intel FeederObservation -> ClaimEvidence -> Claim -> rendered item
```

Do not merge official origin and curated values into one Source. Existing
SourceOriginCluster can group the common origin to prevent counting copies as independent
corroboration; it is not a typed transformation-edge model. Any proposed snapshot metadata
lineage pointers must retain exact origin/curator references and be validated by the existing
repository path. Arbitrary metadata is not an existing FK or proof of transcription accuracy.
ClaimEvidence can reference the curated snapshot/observation; cite the origin separately only
to the extent actually verified. A missing original page/item locator remains a provenance gap.

Raw PDFs/XLSX, free text detail/reasons, addresses, parcel/account identifiers, contacts and
family names are unnecessary for this minimal design. Use policy-permitted normalized values
and capture hash/locator metadata in canonical SourceSnapshot; do not introduce a second raw
store. If redaction prevents reproducibility, retain an unresolved state rather than collecting
more private detail by default.

At most retain coarse reported ownership category (self/spouse/other reported family) when
necessary for a supported aggregate, without relative names, birthdates, sequence identities,
contacts or links. Prefer a family aggregate when finer categories add no public-interest value.
Do not create spouse/parent/child Persons, FamilyRelationship entities or hidden identity joins.
Do not expand the discovery universe to ordinary staff or donors.

Only existing, officially anchored Assembly Persons are eligible for a later linkage review.
OpenWatch crosswalks can support a reviewed exact-code bridge, never name-only matching or
automatic authority. The current automatic materialization gate supports the official roster
semantic scope only; this proposal does not widen it.

## Blocking conditions and reopening criteria

1. Supply a corrected, versioned release manifest with distinct August 2024 and March 2026
   origin references, types, MP-only inclusion rules and original-to-curated counts.
2. Establish release/disclosure/item observation keys and amendment/republication behavior,
   including duplicate items, reordering, replacements and deletions. A documented
   source-derived strategy is acceptable; permanent Person authority is not required for rows.
3. Validate a permitted complete bulk/API route, request limits and per-layer storage/reuse
   terms. Resolve the official origin route without bypassing the robots instruction.
4. Validate exact MONA_CD crosswalk provenance and coverage against the official roster;
   quarantine unmatched/conflicting rows. Never fill gaps by name.

Until those L3 gates are met, no automated enumeration run or scheduler is authorized.
A separately rights-approved official packet may be evaluated for human-assisted L1/L2 under
the [source acquisition playbook](FEEDER_SOURCE_COVERAGE.md#source-acquisition-playbook), without
ingesting OpenWatch or creating Persons. No such importer existed at the 2026-09-12 checkpoint;
the 2026-10-05 decision above adds it (L1, no real packet yet).
A later L3 ExecPlan must prove unfiltered bounded enumeration, transactional
snapshot/observation commit before checkpoints, resume, idempotency, corrected-release handling,
privacy, publication gates and full DoD using the existing foundation.

## Historical subsequent-lane audit — original documentation-only scope

| Candidate | Evidence and limits | Independent future gate |
|---|---|---|
| National Assembly roll-call votes | [Official Open Assembly service](https://open.assembly.go.kr/portal/data/service/selectServicePage.do/OPR1MQ000998LC12535) states that its table covers the 22nd Assembly and its file/API covers the 20th Assembly onward; the [data.go.kr catalog](https://www.data.go.kr/data/15125948/openapi.do) describes member plenary vote results; [OpenWatch documentation](https://docs.openwatch.kr/api-1/national-assembly/votes) remains a curated secondary reference | Official bill/vote/session and MONA_CD anchors; complete vote universe; stable row/version semantics; distinguish absence/abstention; no ideology inference |
| Local-council extra jobs | [Docs](https://docs.openwatch.kr/data/local-council/extra-job): 7th basic councils; 8th basic/metro; FOI snapshots, NGO/SBS contributions | Filing/as-of dates, latest-filing selection, undisclosed vs absent, each contributor's rights and official identity |
| Local-council former/private-sector activity | [Docs](https://docs.openwatch.kr/data/local-council/former-career): 8th term, prior-three-year disclosures; 2022–2023 collection | Preserve FOI non-disclosure/nonexistence (including excluded councils), dates and source boundaries; not a private-employee discovery route |
| Local-council discipline | [Docs](https://docs.openwatch.kr/data/local-council/disciplinaries): FOI plus curator media context; current directory's 8th link aliases 7th | Separate official sanction from curated allegation; appeals/reversals and term completeness |
| Political-contribution aggregate enrichment | [Docs](https://docs.openwatch.kr/data/political-contributions/national-assembly): annual NEC-derived totals; docs end 2024, directory 2025 | Annual coverage, corrections and aggregate licensing; no ordinary donor rows or Person creation |

This table records the original asset-source audit scope. It did not authorize those lanes.
Subsequent actual roll-call ingestion and publication are governed separately by
[Assembly roll-call vote feeder](ASSEMBLY_ROLL_CALL_VOTE_FEEDER.md) and the current
[feeder coverage inventory](FEEDER_SOURCE_COVERAGE.md); use those for current status.

## PETI single-record operator entry

`python -m workers.assembly_asset_import --peti-receipt RECEIPT.json
--peti-policy POLICY.json` validates one supplied closed public-total selector receipt.
The default is a no-write preview. PETI never accepts a Gazette PDF or Gazette rights flag.
The database URL is read from `CIVIC_DATABASE_URL` (or the named `--database-env`), never
passed in PETI command arguments. No network collection or automatic Person linkage occurs.

Capture `--commit` requires an already stored SourcePolicy exactly equal to the explicit
policy file. It commits the existing Source/Snapshot/Observation/checkpoint through the
canonical repository. It cannot create or relax that policy. The capture receipt returns
the exact observation IDs needed for the next operation.
An absent policy can first be reviewed with `--peti-operation policy --command COMMAND.json`.
The canonical `REGISTER_SOURCE_POLICY` command selects exactly the candidate policy ID and
contains the complete typed SourcePolicy JSON in the existing `value` field. This preserves
historical command serialization. The action is closed to the reviewed PETI metadata policy
ID `12ee6a2d-b36f-4bea-9a6e-79d0a2f65f75`, `www.peti.go.kr` and the
`official_public_declared_asset_metadata` source class, with the existing closed PETI receipt
route/field contract. Fetch, fulltext, excerpts and commercialization stay false; license
remains unset. `can_send_to_ai` must be explicitly supplied: false is preserved and true
refers only to the already reviewed public-total metadata scope, not PDF/private detail rights.
The full candidate policy hash and existing/absent ID/domain state are bound into the preview
state hash. Commit uses `--commit --actor OWNER --state-hash EXACT_PREVIEW_HASH`, recomputes
locked current state and never overwrites a different policy. An exact existing match is a
no-write no-op, including no new audit row. New registration writes one SourcePolicy and its
canonical audit atomically; ID/domain uniqueness conflicts roll back. Registration creates
no source run, capture, identity link or Claim. PostgreSQL concurrency execution remains
NOT_RUN until tested on that backend; SQLite locking/rollback is covered by regressions.
The repository repeats complete policy equality inside the same locked transaction:
PostgreSQL locks the stored policy row; SQLite takes its existing immediate write lock.
A policy revoked after CLI precheck blocks capture without advancing a checkpoint.
Aware audit dates compare as UTC instants; unknown naive legacy dates retain wall-clock
semantics rather than acquiring an inferred timezone.

`--peti-operation link --command COMMAND.json` uses canonical `LINK_PERSON` preview/audit.
The command must select one committed PETI observation, a current RESOLVED Person, and one
published official Assembly roster Evidence, with identity basis
`PUBLIC_DISCLOSURE_SOURCE_CONTEXT`. Genuine owner `human_verified: true` records identity
review of this exact source context; it is not a copyright attestation for public facts.
A command without that confirmation returns `OWNER_SOURCE_CONTEXT_REVIEW_PENDING` and
does not construct a confirmed AdminCommand. This basis never permits MERGE or other feeders.
The official provider key, normalized immutable hash, unique active Person link, completed
full-roster checkpoint and successful run are revalidated. The resulting Claim is DRAFT.

`--peti-operation publish --command COMMAND.json` is a separate canonical `PUBLISH` decision.
It revalidates the reviewed link, source closure, printed-total reader, current official
roster anchor and every bounded sibling observation version. Conflicting unpublished
versions fail closed. It preserves CLAIM / asserted-as-true false and UNKNOWN report type.
Reviewed admin commits require `--commit --actor OWNER --state-hash EXACT_PREVIEW_HASH`.
Preview and commit use the existing transaction/audit/concurrency contract, with no new table.

Operator stdout contains only IDs, hashes, counts and statuses. Optional `--preview-output`
writes the full canonical preview to a new owner-local file; existing files are not overwritten.
This separates owner review from AI transport when SourcePolicy.can_send_to_ai is false.
All operational application and publication remain unexecuted until a concrete source-policy,
identity and publication decision; disposable regression DBs do not establish live coverage.
