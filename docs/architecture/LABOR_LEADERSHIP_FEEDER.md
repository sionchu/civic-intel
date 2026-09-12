# Labor Organization / Public Leadership Feeder

## Purpose

Civic Intel may use public labor-organization data to explain career paths through union
leadership, labor federations, social-dialogue bodies and later public office. It does not
compile or infer ordinary union membership.

```text
전국노동조합표준데이터 / official federation or commission source
 -> LaborOrganizationRecord
 -> explicit public representative only
 -> IdentityCandidate
 -> existing Claim / ClaimEvidence or CommitteeMembershipEpisode
 -> public commission / party / elected-office links
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Official structured source

The nationwide labor-union standard dataset on the Public Data Portal aggregates union
records managed by local governments. The reviewed 2026-07 dataset exposes fields including:

- 노동조합명
- 노동조합형태
- 설립일자
- 소속연합단체명
- 대표자명
- 조합원수
- 소속사업장명

It also exposes address, telephone and coordinates. Those location/contact fields are not
needed for public appointment-path analysis and are discarded before staging.

The first implementation keeps live collection and commercial reuse fail-closed until the
exact standard-data adapter and item-level terms are reviewed.

## Organization facts vs person facts

The following are organization-level facts:

- union name/form;
- establishment date;
- affiliated federation;
- membership count;
- publicly listed workplace/enterprise context.

`membership_count` is never attached to an individual person.

The `대표자명` field can create a **leadership IdentityCandidate** because the source
explicitly publishes that person in a representative role. A masked, missing or generic name
does not create a Person candidate.

## Sensitive-affiliation rule

Union membership or affiliation can be sensitive personal information. Therefore:

- ordinary member rosters are prohibited;
- employment at a unionized workplace does not establish union membership;
- demonstration/strike participation does not establish membership;
- donations, social media, photographs or association with a leader do not establish
  membership;
- membership of relatives/colleagues is never inferred;
- a public union representative role must not be generalized into unrelated political
  loyalty, party or faction labels.

Only an explicitly public leadership role with a public-interest purpose may enter the Person
feeder.

## Identity rule

A representative name in the standard dataset is an identity/discovery anchor, not an
automatic merge with every same-name Person already in Civic Intel.

Useful anchors include:

- union name;
- source record identifier;
- public data as-of date;
- later official federation/committee/public-office records.

If the same-name identity cannot be resolved safely, keep it under review.

## Federation and public-policy links

An organization's `소속연합단체명` establishes the union organization's disclosed federation
context. It does **not** automatically create a personal relationship between the union
representative and every federation leader or political figure.

A future public-interest leadership path may be added only from explicit evidence such as:

- federation/confederation official leadership page;
- officially named bargaining representative;
- Economic, Social and Labor Council or government committee appointment;
- official party/campaign/public-office appointment record.

## Career-path value

Supported descriptive routes can include:

```text
union representative
 -> federation/confederation public leadership
 -> government/social-dialogue committee
 -> National Assembly / local elected office / public appointment
```

or:

```text
public-sector union leadership
 -> civic/labor-policy role
 -> local council / National Assembly
```

Historical frequency is descriptive and never appointment probability.

## First implementation

- reviewed metadata-only SourcePolicy for the nationwide standard-data lane;
- privacy-safe normalized fixture parser;
- union organization metadata staging;
- representative-name-only IdentityCandidate staging;
- membership count remains organization-level only;
- address/phone/coordinate and any member-list fields are discarded;
- no DB upsert/publication;
- no federation-site crawler;
- no inference of ordinary membership, ideology, party or faction.

## Federation and social-dialogue source-contract gate (2026-09-12)

The nationwide standard-data lane remains `L1 CONTRACT_STAGED`: its existing contract and
privacy-safe fixture cover organization metadata and an explicitly public representative, but
there is no live collection or persistent feeder path. The following official routes were
evaluated as independent source lanes. They are not one combined labor-leadership roster.

| Source lane | Official boundary and observed contract | Gate result |
|---|---|---|
| 민주노총 current / historical leadership | [`staff_now`](https://nodong.org/staff_now) is a finite current-leadership page labelled `11기 14대`; [`staff_history`](https://nodong.org/staff_history) lists prior terms and interim periods. The pages expose names, roles and some term-period text, but no API, pagination, stable person/row IDs, explicit effective/as-of timestamps, or correction/republication contract. Terms and privacy links are visible, but a reuse license was not identified in the inspected pages. | `L0 RESEARCHED` source lane. A finite, rights-reviewed page packet could support human-assisted staging; no automatic L3 path. |
| 경사노위 committee / appointment posts | The official [committee structure](https://www.eslc.go.kr/ibuilder.do?menu_idx=2230) defines bodies and composition. The official [2026-03-19 launch post](https://www.eslc.go.kr/bbs/data/view.do?bbs_mst_idx=BM0000000412&data_idx=BD0000000001&menu_idx=2264) and [regional-dialogue support-group post](https://www.eslc.go.kr/bbs/data/view.do?SC_KEY=&SC_KEYWORD=&bbs_mst_idx=BM0000000217&data_idx=BD0000001000&memberAuth=Y&menu_idx=2286&pageIndex=1&per_menu_idx=2074&root_yn=Y&stype=&submenu_idx=&tabCnt=2) are dated posts with attachments, including HWP. The board is page-based and post-level `data_idx` identifies a post, not a member row. No single current/historical member universe, member-row IDs, or correction/republication contract was found. The site states all-rights-reserved copyright; no reuse license was identified. | `L0 RESEARCHED` source lane. A single rights-approved post/attachment packet could support human-assisted staging; it does not establish L3. |
| 한국노총 official footprint | Official central, publication and affiliate subdomains expose organization identity, event articles and bounded local-election/affiliate facts, but the inspected pages do not expose a central stable leadership roster. Fragmented site boundaries, article-level references and the absence of a central pagination/key/version contract prevent universal enumeration. | `DISCOVERY_ONLY` for central-roster acquisition. A named, bounded official event or appointment page may be cited independently after review; no feeder promotion. |

### Contract if a lane reopens

- **Authoritative source and boundary:** 민주노총 supplies only the leadership stated on its own
  current/history pages; 경사노위 supplies only the dated committee or appointment event stated by
  the responding official post and its exact attachment; 한국노총 pages remain bounded event or
  affiliate evidence until a central roster is published. Do not use the nationwide dataset's
  `소속연합단체명` to create a person-level federation link.
- **Normalization:** use a fixed minimal dictionary of public name, public role, organization/body,
  term or event date when explicitly stated, source URL, and page/post/attachment locator. HWP,
  PDF or HTML extraction is analyst-reviewed transcription, not an authority upgrade. Preserve
  explicit missingness such as `정보없음`, unreadable, withheld and not-collected; do not infer a
  date, role or leadership continuity.
- **Provenance:** retain the official page/post/attachment as the origin Source/Snapshot and any
  analyst-normalized representation as a separate Source/Snapshot. A post ID or attachment name
  is a packet locator, not a Person ID. Fulltext or attachment retention requires a separate
  SourcePolicy rights decision; no raw payload was added by this gate.
- **Identity:** official Civic Intel identity anchors take priority. Dataset/page-local IDs and the
  standard-data `record_id` are provider or crosswalk keys only. Name-only linking, event
  co-mention, organization proximity and inferred union membership cannot resolve a Person.
  Family members and ordinary union members are outside the discovery universe.
- **Version and correction:** capture date, publication/registration date and stated term/event
  date separately. A new page or attachment byte set creates a new source snapshot; a changed
  normalized value creates a new immutable observation with an explicit replacement/correction
  reason. No old observation is overwritten, and an absent provider row key cannot be promoted to
  a permanent identity key.
- **Maturity ceiling:** the aggregate labor lane remains `L1 CONTRACT_STAGED`. These federation and
  committee lanes have an automation ceiling of bounded human-assisted L1/L2 only after rights,
  manifest and reviewer gates close. They remain blocked from L3 until a complete declared
  universe, deterministic pagination or document manifest, stable record semantics, correction
  behavior, permitted route and offline coverage tests exist.
- **Privacy and publication:** retain only public senior leadership or named committee appointment
  facts needed for the public-interest question. Do not retain ordinary member rosters, sensitive
  affiliation, private contact/location fields, unnecessary biographies or photos. Human review
  does not make an unresolved observation an automatic FACT or authorize Person materialization.

No live adapter, crawler, importer, fixture, migration or new labor leadership persistent model
was added by this gate. If a source contract later closes, reuse the existing
`SourceRun`/`SourceCheckpoint`/`FeederObservation` foundation, `LaborOrganizationRecord` staging,
and the existing Claim/Evidence or `CommitteeMembershipEpisode` semantics. Do not create a new
`LaborLeadershipEpisode` or generic roster abstraction merely to represent these pages.
