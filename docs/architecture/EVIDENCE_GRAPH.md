# Evidence Graph — Person ↔ Organization affiliations and derived relations

Canonical boundary for the public-interest relationship layer: who belonged to which official
body, when, and which published facts make two People structurally connected. Prior-art and
literature review: [EVIDENCE_GRAPH_PRIOR_ART](../research/EVIDENCE_GRAPH_PRIOR_ART.md).

## Principle

```text
Public Source → SourceSnapshot → FeederObservation → Claim (FACT / attributed CLAIM) + ClaimEvidence
  → Affiliation (Person ↔ via entity, read-time)            packages/rendering/relationship_projection.py
  → DerivedRelation (versioned rule, read-time)            same module
  → API: /relationships/people/{id} · /compare · /path · /rules
```

- **No second truth store, no migration, no graph DB.** Affiliations and relations are computed on
  each read from current published Claims that pass `validate_claim_publication`. Nothing is
  written. The legacy `relationships` table / `GET /people/{id}/relationships` (Golden typed
  stakeholders) is unchanged.
- **Person ↔ Person is never primary data** (Breiger duality). It is a projection over a shared
  via entity, and every relation carries `source_claim_ids`, `evidence_ids`, `rule_id`,
  `rule_version` and its temporal basis.
- **FACT / DERIVED / CANDIDATE.** Input Claims are FACT (asserted provider record) or attributed
  CLAIM. A relation is `DERIVED` only when both via ends have a bindable identity; otherwise it is
  `CANDIDATE`, excluded from default responses and never promoted automatically.
- **No interpretation.** Relation names describe structure (`SAME_PARLIAMENTARY_COMMITTEE`,
  `BOARD_INTERLOCK`), never friendship, influence, faction or motive. Each payload carries the
  interpretation note and limitations. There is no combined "closeness" score; the per-relation
  `scores` keep evidence confidence, structural proximity (1–3) and temporal currency separate.

## Via-entity binding contract

A via entity joins two People only by one of these exact bindings
(`Binding` in the projection module):

| Binding | Example via key | Source |
|---|---|---|
| `CANONICAL_ORGANIZATION` | `organization:{uuid}` | ALIO reviewed role `organization_id`; witness Claim → its source Organization Claim |
| `PROVIDER_CODE` | `assembly_committee:{DEPT_CD}`, `opendart_corp:{corp_code}`, `assembly_bill:{BILL_ID}` | official provider codes |
| `SOURCE_SCOPED_EXACT_VALUE` | `assembly_roster_party:{POLY_NM}` | exact categorical value within the current-roster contract only |
| `EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK` | `organization:{uuid}` + `committee_code` | committee `DEPT_CD` name equals exactly one current Organization `국회 {name}` |
| `EXACT_REGISTRY_NAME` | `organization:{uuid}`, `opendart_corp:{code}`, `mois_org:{code}` | a biography span equals exactly one registry entry (see below) |
| `EXACT_UNIVERSITY_NAME` | `university:{정식명}` | full domestic university name not in the MOIS registry |
| `ELECTION_PARTY_CAMPAIGN` | `campaign:{sgId}:{정당}`, `transition:{sgId}` | reviewed NEC election + exact party (or reviewed presidential nominee); presidential transition body |
| `SOURCE_TEXT_UNBOUND` | `school_text:…`, `career_text:…` | anything else (high schools, foreign schools, law firms, unmatched names) → CANDIDATE |

This satisfies the [Governance Ontology](GOVERNANCE_ONTOLOGY.md) precondition for cross-Person
path search: Claim-scoped labels are never merged by string equality; only the bindings above are.

### Registry binding of biography text (`relationship_bindings.py`)

Registries already held, in precedence order (a lower tier wins for one name; two different
entities at the winning tier are ambiguous and never bind):

0. canonical current Organizations with an ALIO classification Claim → `PUBLIC_INSTITUTION`;
1. OpenDART listed-company master names (`corp_code`) → `COMPANY` (same node as disclosed executives);
2. MOIS standard organization codes, representative institutions (`org_code`): government types →
   `GOVERNMENT_BODY`, 산하기관/정부투자기관 → `PUBLIC_INSTITUTION`, 고등교육기관 → `UNIVERSITY`;
3. MOIS subordinate government units by their own name (courts, prosecutors' offices, regional
   agencies), names of 5+ characters only.

A biography line binds through its longest word span (legal-form markers such as `(주)` and
brackets split words; a trailing role word such as `장관`/`대표이사` is stripped from one-word
spans) that names exactly one entry. Reviewed aliases: `청와대`, `대통령실` → 대통령비서실.
Universities bind on the MOIS 고등교육기관 name (or a reviewed short form such as 서울대 → 서울대학교);
high schools never bind (same names in many regions). Campaigns bind on a reviewed election table
(대선 15–21대, 총선 18–22대, 지방선거 5–9회) plus an exact party name, or a reviewed presidential
nominee name for that election; regional transition committees never bind, presidential ones bind
on the ordinal, the president-elect's name, or 국정기획자문위원회(2017)/국정기획위원회(2025).
Binding identifies the named entity; the biography line remains an attributed, non-asserted CLAIM.

## Affiliation extractors (exact source contracts; anything else fails closed)

| Predicate | Contract | Via kind | Temporal basis |
|---|---|---|---|
| `ASSEMBLY_COMMITTEE_MEMBERSHIP` (new) | `assembly_committee_member_list_membership` | PARLIAMENTARY / SPECIAL_COMMITTEE | as-of collection; same SourceRun = co-listed |
| `ASSEMBLY_PARTY` | `assembly_member_roster` / `field_name=party` | PARTY | as-of roster run |
| `ALIO_REVIEWED_PERSON_ROLE` | `alio_reviewed_person_role` | PUBLIC_INSTITUTION | disclosure `as_of`; same institution + `as_of` = co-listed |
| `OPENDART_DISCLOSED_EXECUTIVE_ROLE` | `opendart_reviewed_executive_role` | COMPANY | settlement date; same `rcept_no` = co-listed; tenure start when stated |
| `LISTED_AS_GUKGAM_WITNESS` | `gukgam_witness_reviewed_person_link` | committee Organization | list adoption date |
| `ASSEMBLY_BILL_PARTICIPATION` | `assembly_term_bill_participation` | BILL | proposal date |
| `ASSEMBLY_BIOGRAPHY_EDUCATION` (new) | `assembly_member_profile_biography` | EDUCATIONAL_INSTITUTION (unbound) | stated period only |
| `ASSEMBLY_BIOGRAPHY_CAREER` (new) | `assembly_member_profile_biography` | CAMPAIGN / TRANSITION / GOVERNMENT_COMMITTEE / CAREER_ORGANIZATION (unbound) | stated period only |

Organization ↔ Organization edges used only for path search: `LISTED_AS_GUKGAM_AUDIT_TARGET`
(institution → auditing committee via the committee-name crosswalk).

## Temporal rules

Overlap is `VERIFIED` only from (a) a shared source capture (same full-enumeration SourceRun,
same ALIO disclosure `as_of`, same OpenDART `rcept_no`), (b) two fully known intervals that
intersect, or (c) an `as_of` date inside a known interval. Otherwise it is `UNKNOWN`; disjoint
known intervals are `NOT_OVERLAPPING`. Biography dates are widened conservatively: a stated start
moves to the end of its unit (`2020.5` → 2020-05-31) and an end stays at the start of its unit, so
month/year precision can never manufacture an overlap. Missing dates are never guessed; a past
role is never shown as current (`current_marker` is copied, not inferred).

## Rule registry (`RULES`, ruleset 1.0)

`GET /relationships/rules` serves the executable registry: `rule_id`, `rule_version`, inputs,
conditions, outputs, `false_positive_conditions`, overlap variant and `path_default`.

| Rule | Relation (overlap variant) | Status | Path default |
|---|---|---|---|
| shared_parliamentary_committee | SAME_PARLIAMENTARY_COMMITTEE | DERIVED | yes |
| shared_special_committee | SAME_SPECIAL_COMMITTEE | DERIVED | yes |
| shared_party | SAME_PARTY | DERIVED | no (hub) |
| shared_public_institution | SAME_PUBLIC_INSTITUTION (PUBLIC_INSTITUTION_OVERLAP) | DERIVED | yes |
| shared_company_board | SAME_COMPANY_BOARD (BOARD_INTERLOCK) | DERIVED | yes |
| committee_witness_request | COMMITTEE_WITNESS_REQUEST (member ↔ witness of that committee) | DERIVED | yes |
| bill_cosponsorship | BILL_COSPONSORSHIP / REPEATED_COSPONSORSHIP (≥10 bills) | DERIVED | no (event) |
| shared_school (1.1) | SAME_UNIVERSITY / SAME_GRADUATE_SCHOOL / SAME_DEPARTMENT / SAME_HIGH_SCHOOL (EDUCATION_TIME_OVERLAP) | DERIVED when bound, else CANDIDATE | no |
| shared_government_body | SAME_GOVERNMENT_BODY (GOVERNMENT_OVERLAP) | DERIVED when bound | yes |
| shared_career_org (1.1) | SAME_CAMPAIGN / SAME_TRANSITION_COMMITTEE / SAME_GOVERNMENT_COMMITTEE / SAME_EMPLOYER (`*_OVERLAP`, EMPLOYMENT_OVERLAP) | DERIVED when bound, else CANDIDATE | yes when bound |
| revolving_door | GOVERNMENT_TO_BUSINESS / BUSINESS_TO_GOVERNMENT / PUBLIC_INSTITUTION_TO_PRIVATE / PRIVATE_TO_PUBLIC (per Person, stated periods strictly ordered by month) | DERIVED when both ends bound | — |

Explicitly **not** relations: witness ↔ witness co-listing, news/photo co-occurrence, same
apartment complex, inferred religion, vote similarity, same birth region/hometown. Pair
generation starts from shared via entities (`index_by_via`), never an N² Person scan.

Not yet executable (no producing source): FAMILY (explicit public records only),
ASSOCIATION/FOUNDATION membership with registry binding, OWNERSHIP/MAJOR_SHAREHOLDER (OpenDART
`elestock`/major-holder lanes need `DART_API_KEY` on the collector), DECLARED_PROPERTY (국회공보
route blocked; human-assisted packets only). Each needs its own source contract first.

## Biography lane (member-profile `MEM_TITLE`)

`workers/assembly_member_biographies.py --enumerate` stores one metadata-only observation per
current member: `MONA_CD` + verbatim lines (HTML decoded; contact/URL/over-long lines dropped).
Contact, staff and address fields are never read. `--publish [--dry-run]` builds non-asserted
`CLAIM`s for exact current-roster members only ("국회 의원 인적사항의 {이름} 약력에 「…」 항목이
기재되어 있다"), following the [Career Facets](CAREER_FACETS.md) provenance rule for
self-reported records. Parser `assembly_biography_parser_v1` is deterministic: sections from
headers, stated periods with precision, `현/전` markers, education only with a school token and
(outside a 학력 section) a degree word, honorary degrees and teaching posts excluded, career
categories by fixed keyword order. Institution names are copied exactly; `institution_key` is a
comparison key, not an identity. A later biography change fails closed (new observation version)
like the other `AssemblyMemberClaimLane` lanes and needs a reviewed supersession.

**Owner decision (2026-10-07):** verbatim biography lines may be shown publicly. The Assembly
member API license is unrestricted (data.go.kr 15126133); the SourcePolicy keeps
`can_show_excerpt=false` for raw responses, and the biography Claims quote one line in the
proposition with `excerpt=None`. Applied to canonical on 2026-10-07 after backup
`pre-evidence-graph-20261007-080654.dump`.

## API

| Route | Returns |
|---|---|
| `GET /relationships/people/{id}?layer=&relation_type=&include_candidates=&limit_per_via=` | own affiliations, relations grouped by via entity with counterpart, cosponsorship pairs |
| `GET /relationships/compare?a=&b=` | direct relations, shared organizations, multiplex layers, timeline, cosponsorship, shortest evidence path |
| `GET /relationships/path?from=&to=&include=PARTY,BILL&max_edges=` | nodes, edges (each with Claim/Evidence ids), `path_length`; `NO_EVIDENCE_PATH_WITHIN_COLLECTED_SCOPE` when none |
| `GET /relationships/rules` | rule registry + live coverage counters |

Only public RESOLVED People appear. `workers/relationship_coverage.py` is the read-only audit that
produces the coverage matrix and relation-layer coverage below.

## Privacy and neutrality

Family, religion, residence and private contact data are not collected by this layer; the
projection has no extractor for them and tests assert such predicates never become affiliations.
Every rule applies identically regardless of party.

## Current measurement

See [EVIDENCE_GRAPH_STATUS](../research/EVIDENCE_GRAPH_STATUS_2026-10-07.md) for the measured
before/after on the canonical DB and its disposable rehearsal copy.
