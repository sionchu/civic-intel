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
| `SOURCE_TEXT_UNBOUND` | `school_text:서울대학교`, `career_text:CAMPAIGN:…` | member-maintained biography text; **not bindable** → CANDIDATE |

This satisfies the [Governance Ontology](GOVERNANCE_ONTOLOGY.md) precondition for cross-Person
path search: Claim-scoped labels are never merged by string equality; only the bindings above are.
A school, campaign or employer named in free text becomes bindable only after an official
registry binding exists (for schools, e.g. a 대학알리미/학교알리미 institution code).

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
| shared_school_candidate | SAME_SCHOOL / SAME_DEPARTMENT (EDUCATION_TIME_OVERLAP) | CANDIDATE | no |
| shared_career_org_candidate | SAME_CAMPAIGN / SAME_TRANSITION_COMMITTEE / SAME_GOVERNMENT_COMMITTEE / SAME_EMPLOYER (`*_OVERLAP`) | CANDIDATE | no |

Explicitly **not** relations: witness ↔ witness co-listing, news/photo co-occurrence, same
apartment complex, inferred religion, vote similarity, same birth region/hometown. Pair
generation starts from shared via entities (`index_by_via`), never an N² Person scan.

Not yet executable (no producing source in this slice): REVOLVING_DOOR transitions,
GOVERNMENT_OVERLAP, FAMILY (explicit public records only), ASSOCIATION/FOUNDATION membership,
OWNERSHIP/MAJOR_SHAREHOLDER, DECLARED_PROPERTY. Each needs its own source contract first.

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

**Owner decision before canonical apply:** the Assembly member API SourcePolicy has
`can_show_excerpt=false` as a data-minimization choice. The biography Claims quote one line in the
proposition and keep `excerpt=None`; the license is unrestricted (data.go.kr 15126133), but
publishing verbatim biography lines is a presentation choice the owner should confirm.

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
