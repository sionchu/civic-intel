# National Assembly asset disclosure source gate

## Decision — 2026-09-12

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
`pdfId=379431`, and 2025 March `pdfId=379578`. No 2026 original issue was established.
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

Until those gates are met, no SourceRun, checkpoint advancement, materialization or scheduler
is authorized. A later L3 ExecPlan must prove unfiltered bounded enumeration, transactional
snapshot/observation commit before checkpoints, resume, idempotency, corrected-release handling,
privacy, publication gates and full DoD using the existing foundation.

## Subsequent lanes — documentation only

| Candidate | Evidence and limits | Independent future gate |
|---|---|---|
| National Assembly roll-call votes | [API](https://docs.openwatch.kr/api-1/national-assembly/votes) documents member/bill/date/result; not an asset source | Official bill/vote/session and MONA_CD anchors; full vote universe; distinguish absence/abstention; no ideology inference |
| Local-council extra jobs | [Docs](https://docs.openwatch.kr/data/local-council/extra-job): 7th basic councils; 8th basic/metro; FOI snapshots, NGO/SBS contributions | Filing/as-of dates, latest-filing selection, undisclosed vs absent, each contributor's rights and official identity |
| Local-council former/private-sector activity | [Docs](https://docs.openwatch.kr/data/local-council/former-career): 8th term, prior-three-year disclosures; 2022–2023 collection | Preserve FOI non-disclosure/nonexistence (including excluded councils), dates and source boundaries; not a private-employee discovery route |
| Local-council discipline | [Docs](https://docs.openwatch.kr/data/local-council/disciplinaries): FOI plus curator media context; current directory's 8th link aliases 7th | Separate official sanction from curated allegation; appeals/reversals and term completeness |
| Political-contribution aggregate enrichment | [Docs](https://docs.openwatch.kr/data/political-contributions/national-assembly): annual NEC-derived totals; docs end 2024, directory 2025 | Annual coverage, corrections and aggregate licensing; no ordinary donor rows or Person creation |

No candidate in this table is promoted, fetched as a new runtime lane or implemented.
