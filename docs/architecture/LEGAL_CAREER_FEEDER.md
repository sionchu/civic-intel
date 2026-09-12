# Legal / Judicial / Prosecution Career Feeder

## Purpose

Civic Intel treats legal careers as time-bounded professional and public-service episodes.
It does **not** flatten judges, prosecutors, lawyers, judicial administrators and legal-policy
roles into one generic `LAWYER` label.

```text
MOJ / Supreme Court / Court Gazette / public professional source
 -> LegalPersonnelRecord or verified professional record
 -> IdentityCandidate
 -> LegalCareerEpisode
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Career types

The canonical contract distinguishes:

- `JUDGE`
- `COURT_PRESIDENT`
- `SUPREME_COURT_JUSTICE`
- `JUDICIAL_ADMINISTRATION`
- `PROSECUTOR`
- `CHIEF_PROSECUTOR`
- `PROSECUTOR_GENERAL`
- `MINISTRY_OF_JUSTICE_LEGAL_ROLE`
- `LAWYER`
- `LAW_FIRM_PARTNER`
- `PUBLIC_DEFENDER_OR_LEGAL_AID`
- `CONSTITUTIONAL_COURT_ROLE`
- `LEGAL_ACADEMIC`
- `GOVERNMENT_LEGAL_ADVISER`

Career event types remain separate from the career type:

- appointment / new assignment
- transfer
- promotion
- assignment
- concurrent appointment / concurrent release
- retirement
- professional registration

A person's timeline may contain several of these types over time.

## Official prosecution lane

Ministry of Justice prosecutor-personnel releases are strong evidence for dated appointment
and transfer events. Reviewed 2026 examples include the 2026-01-29 first-half prosecutor
personnel announcement and the 2026-08-24 second-half general-prosecutor transfer
announcement.

Normalize only public-interest personnel fields:

- name
- effective date
- destination prosecution office / Ministry of Justice role
- title
- previous office/title when explicitly published
- appointment/transfer type
- official assignment domain when explicitly published
- source reference

The personnel release establishes the role transition. It does **not** establish individual
responsibility for every investigation or prosecution conducted by the office.

## Official judiciary lane

Supreme Court personnel releases and Court Gazette personnel orders are strong evidence for
judicial appointments, transfers, judicial-administration posts and concurrent assignments.
The reviewed 2026-01-30 release and February Court Gazette use a structured pattern such as:

```text
previous affiliation/title
 -> person name
 -> appointment order
 -> effective date
```

Preserve the effective date and the exact public-office transition. Do not overwrite a
career timeline with only the latest court/title.

## Lawyer / law-firm lane

The first implementation does not crawl lawyers or law-firm staff.

Future verification may use:

- Korean Bar Association public lawyer/law-firm search for public professional identity;
- official law-firm biographies for publicly presented role and career history;
- official appointment or court record where public representation is directly relevant.

Professional registration or law-firm affiliation does **not** create:

- a private client roster;
- a political relationship edge;
- a faction/ideology label;
- an inference that the person personally handled every matter of the firm.

## Case and decision attribution

Case-level evidence is a separate future lane from career evidence.

Rules:

- judge participation in a published decision != political ideology;
- assignment to a court division != personal responsibility for every case in that division;
- prosecutor assignment to an office/unit != personal responsibility for every case there;
- law-firm affiliation != representation of every firm client;
- reported win/loss, sentencing or indictment rates are not supported as V0 person scores;
- sealed/non-public case material is out of scope.

If a future public-interest case record is added, its role must be explicitly attributed and
kept separate from the generic career episode.

## Disciplinary / controversy data

No disciplinary parser is included in this PR. If official bar/judicial/prosecution
disciplinary records are ever used, preserve the precise disposition, status, date,
reversal/appeal context and source. An allegation or pending process cannot be silently
presented as established wrongdoing.

## Privacy and neutrality

Do not collect or publish:

- private client lists;
- personal address/phone/email;
- family data unrelated to an official public record;
- sealed case information;
- ideology scores;
- guilt-by-association through a former court, prosecution office or law firm.

The feeder describes public roles and dated transitions, not political desirability.

## First implementation

The first implementation is deliberately staging-only:

- canonical `LegalCareerType`, `LegalCareerEventType`, and `LegalCareerEpisode` contract;
- normalized Ministry of Justice prosecutor-personnel fixture/parser;
- normalized Supreme Court personnel fixture/parser;
- mapping to the existing `IdentityCandidate`;
- privacy-safe review JSON;
- SourcePolicies keep live fetch/fulltext/AI/commercial reuse fail-closed until each adapter's
  rights and format are reviewed;
- no automatic DB upsert/publication;
- no broad legal-professional crawler.

## MOJ / Supreme Court source-contract gate (2026-09-12)

The existing legal-personnel lane remains `L1 CONTRACT_STAGED`. Its normalized
`LegalPersonnelRecord`, `LegalCareerEpisode`, identity staging and privacy regressions are
usable, while both live policies remain fail-closed. The two official lanes below must not be
combined into one personnel universe.

| Lane | Official source contract | Gate result |
|---|---|---|
| 법무부 검찰 인사 | The [2026 상반기 검사 인사](https://www.moj.go.kr/bbs/moj/182/602956/artclView.do) detail page identifies the publication date, responsible department, a `공공누리 2유형` label and six linked PDF/HWPX/HWP attachments. It states 569 고검검사급 and 358 일반검사 전보 with separate effective dates. The detail/attachment route is a bounded personnel-round packet, not a published unfiltered prosecutor universe or documented API. The inspected route exposes no provider Person ID, row-level key, replacement history or complete correction contract. | `L1 CONTRACT_STAGED`. One exact rights-approved release packet can support human-reviewed L2 staging; no L3 promotion. |
| 대법원 법관 / 법원행정 | The [2026-01-30 personnel release](https://www.scourt.go.kr/portal/news/NewsViewAction.work?gubun=6&seqnum=2927) describes several effective dates and links release PDFs. The [2026-02-15 Court Gazette](https://www.scourt.go.kr/upload/gongbo/Scourt08460/20260215.pdf) exposes machine-readable tables with issue/order headings, names, previous positions and orders. Later [2026-03-15 Gazette](https://www.scourt.go.kr/upload/gongbo/Scourt08500/20260315.pdf) includes a `발령변경` entry that corrects an earlier order date. The Gazette is an issue/document stream containing multiple order types, not one declared current roster; an exhaustive issue manifest, pagination/cursor contract and row ID are not published in the inspected route. | `L1 CONTRACT_STAGED`. A single rights-reviewed issue or release packet can support human-reviewed L2 staging; no L3 promotion. |

### Reusable contract if a legal lane reopens

- **Authority and boundary:** the issuing institution's release or Court Gazette order is
  authoritative for the named appointment, transfer, assignment, effective date and explicitly
  stated previous office. A release summary does not establish personal responsibility for every
  case handled by an office. Fix the personnel-round, Gazette issue, order type and date scope
  before collection; do not treat the archive as an implicit full roster.
- **Normalization and provenance:** preserve the official detail page and exact attachment or
  Gazette issue as the origin Source/Snapshot. Normalize only name, organization, title, previous
  office/title, event type, effective/event date and public assignment domain when explicit. A
  PDF/HWPX/HWP table is deterministically extracted and human-compared; the analyst value remains
  a separate representation with page/table/row locator and parser/review revision.
- **Identity:** post IDs, attachment IDs, Gazette issue/order numbers and source-derived row
  ordinals identify a source packet, not a canonical Person. A future record key may be
  `{post_or_issue}:{attachment_or_order}:{row_ordinal}` within the captured scope. Existing
  official identity anchors take priority; name-only linking, office proximity and case
  co-mention cannot resolve a Person.
- **Version and correction:** keep publication/registration, effective/event and capture times
  separate. A replacement attachment or later Gazette correction creates a new SourceSnapshot and
  immutable observation with an explicit replacement/correction relation. The 2026 Gazette
  `발령변경` pattern must be tested as a correction, not silently merged into the earlier order.
- **Rights and storage:** the MOJ page's `공공누리 2유형` still requires source attribution and
  restricts commercial use; it does not require retaining full attachments for this product. The
  [Court copyright policy](https://www.scourt.go.kr/portal/popup/jeojak_pop.html) permits free use
  only where the Court owns all copyright, with specific source attribution, and asks users to
  consult the Court for other material. Keep current metadata-only/fulltext-disabled policies
  until the exact packet and storage purpose are reviewed.
- **Maturity ceiling:** a rights-approved finite release/issue packet may be a human-assisted L2
  source observation path. L3 requires a declared complete universe, issue/page coverage, stable
  record semantics, correction/withdrawal behavior, permitted route and offline multi-page
  regression. No scheduler, broad legal-professional crawl or generic document importer is
  implied.

No live adapter, attachment downloader, migration or new legal schema was added by this gate. If
the next packet is approved, reuse `LegalPersonnelRecord`, `SourceRun`, `SourceCheckpoint` and
`FeederObservation`, then publish only through the existing identity and Claim/Evidence gates.

### MOJ packet preflight (2026-09-12)

The first bounded packet candidate is the official post `602956`, “2026년 상반기 검사 인사”.
Its page exposes six attachment references (`490100`–`490105`): a PDF/HWPX release pair and
four HWP movement tables. The page labels the work `공공누리 2유형`; the [official type-2
terms](https://www.kogl.or.kr/info/licenseType2.do) allow attribution and non-commercial use,
but exact attachment ownership and any third-party material still require the packet-specific
rights check.

This is a candidate manifest, not an acquired packet. The current MOJ `SourcePolicy` keeps
`can_fetch=False`, `can_store_fulltext=False` and `can_commercialize=False`, so the download,
Synap preview and attachment bytes were not accessed or retained. The L2 gate therefore remains
closed until the exact attachment set, permitted storage/normalization purpose, attribution and
third-party-rights boundary are represented in a reviewed policy decision. A page-level license
label alone does not authorize an automatic production adapter or public redistribution of the
attachments.

### MOJ packet rights revalidation (2026-09-13)

The official detail page was re-opened and still exposes the same six attachment references and
the explicit `공공누리 2유형` work label. The [official type-2 terms](https://www.kogl.or.kr/info/licenseType2.do)
permit sharing and derivative use with attribution, but restrict that permission to non-commercial
use. The [MOJ copyright policy](https://www.moj.go.kr/moj/129/subview.do) separately states that
unrestricted use applies to works for which the Ministry holds all economic rights, that each work's
KOGL mark must be checked, and that unmarked material requires consultation with the responsible
staff.

The inspected detail page did not state per-attachment ownership, third-party material or a
storage/normalization/redistribution scope. A metadata-only `HEAD` probe of each attachment route
returned a self-redirect and no usable content metadata; no response body, preview or attachment
bytes were retrieved. The route behavior is an access limitation, not evidence of a rights denial,
and does not close the rights gate.

The post identifies `검찰과` as its publishing department and provides a packet-specific
consultation route. No external inquiry was sent as part of this gate; the department listing is
only an official routing signal, not a rights decision.

**Decision:** keep the existing MOJ `SourcePolicy` fail-closed (`can_fetch=False`,
`can_store_fulltext=False`, `can_commercialize=False`) and keep this lane at `L1 CONTRACT_STAGED`.
No L2 packet staging or L3 promotion is authorized. Reopen only after an official, packet-specific
rights decision (or clear per-attachment license/ownership record) covers the exact files, the
intended non-commercial storage and normalization purpose, attribution, and any third-party-rights
boundary. Until then, do not request the attachment body or add a downloader/extractor.
