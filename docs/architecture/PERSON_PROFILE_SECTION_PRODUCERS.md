# Person profile section producers

Updated on 2026-10-08 for the source-attributed career projection. This is the canonical inventory
of which upstream producer feeds each Person profile section rendered by
`packages/rendering/profile_projection.py`.
A section label in the UI is not evidence that a collection pipeline exists.

## Two lanes

- **Source-backed factual lane**: `SourcePolicy → Source → SourceSnapshot → FeederObservation →
  identity → Claim → ClaimEvidence → publication gate → section`. Only this lane may produce FACT
  or source-attributed CLAIM entries.
- **Derived Intelligence lane**: published/eligible Claim + Evidence → deterministic eligibility
  → reviewed derived artifact (method version, input IDs, coverage, limitations) → section.
  A derived result is never a FACT, and model output never becomes one automatically
  ([North Star](../product/CIVIC_INTEL_NORTH_STAR.md)).

## Producer matrix (general Person profile)

People with any published Assembly roster or bill Claim take the separate Assembly profile
(`overview`, `current_role`, `career_timeline`, `legislative_activity`, `recent_changes`,
`limitations`), fed by the Assembly roster, historical and bill-participation feeders.
`current_role` also shows committee offices (`ASSEMBLY_COMMITTEE_ROLE`, 위원장·간사) from the
committee member-list lane ([feeder](ASSEMBLY_COMMITTEE_ROSTER_FEEDER.md)), once that lane is run.
`decision_episodes` (의사결정 에피소드: 본회의 표결) shows the 10 most recent published
`ASSEMBLY_PLENARY_VOTE` Claims with whole-record counts
([feeder](ASSEMBLY_ROLL_CALL_VOTE_FEEDER.md#vote-claims-separate-publication-step)); the section is
emitted only when such Claims exist. Repeated patterns stay eligibility-only: vote Claims are not
turned into alignment or party-line patterns.

| Section | Renderer input | Current producer | Lane | State | Missing step |
|---|---|---|---|---|---|
| identity | Person | identity materialization | source | WORKING | — |
| gukgam_2026 / public_institution_roles / corporate_roles | `LISTED_AS_GUKGAM_WITNESS`, `ALIO_REVIEWED_PERSON_ROLE`, `OPENDART_DISCLOSED_EXECUTIVE_ROLE` | witness/OpenDART reviewed LINK_PERSON, ALIO source-context materialization | source | WORKING (rendered only when non-empty) | publication of the 2,688 ALIO role Claims is an owner decision |
| assembly_base_profile | Assembly roster Claims | Assembly roster feeder | source | NOT_APPLICABLE in this path by construction | — |
| summary | `NOMINATED_AS`, `APPOINTED_AS`, … | Golden Set and `ReviewedPersonBundle` | source | PARTIAL | only explicit public-office/nomination records; historical terms do not become current roles |
| career_timeline | legacy career predicates plus `ASSEMBLY_BIOGRAPHY_CAREER`, `NEC_CANDIDATE_CAREER`, `ASSEMBLY_HISTORICAL_TERM` | reviewed fixtures, Assembly biography, NEC candidate submissions, Assembly former-member terms | source | WORKING for published linked Claims | source-attributed biographies stay CLAIM; ALIO/OpenDART disclosures remain in their own source sections |
| recent_changes | dated historical `HELD_ROLE`/`APPOINTED_AS` with `change_input_scope` | Assembly historical reviewed packet + `SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1` | derived | PARTIAL | a second Person lane with two comparable dated Claims of the same dimension |
| current_power_tasks | `HAS_AUTHORITY`…`SUPERVISES`; OpenDART `responsibility` | reviewed fixtures; **OpenDART reviewed executive link (this change)** | source | PARTIAL | statute/organization-chart sources for public officials (BLOCKED_SOURCE) |
| appointment_logic | `APPOINTMENT_RATIONALE`, … | Golden supplement only | source (attributed text) | NO_PRODUCER | a reviewed official personnel-announcement lane quoting the stated rationale |
| decision_episodes | `DecisionEpisode` + published Claim + exact ClaimEvidence | Golden seed only for this path; Assembly members get plenary-vote episodes from `ASSEMBLY_PLENARY_VOTE` Claims | source | NO_PRODUCER here / PARTIAL for Assembly | a non-Assembly event lane (official appointment/governance decisions) |
| repeated_patterns | ≥2 eligible episodes with independent origins | eligibility only (`validate_pattern`) | derived | DERIVATION_ONLY | decision episodes, then a reviewed pattern artifact |
| stakeholders | typed `Relationship` with ClaimEvidence refs, never `CO_MENTION` | Golden seed only; derived structural relations are served separately by `/relationships/*` ([Evidence Graph](EVIDENCE_GRAPH.md)) | source / derived | NO_PRODUCER for this section | profile rendering of the derived relations after the canonical membership/biography apply |
| controversies | controversy predicates or SUPPORT+REFUTE evidence | `ReviewedPersonBundle` (김현지) only | source | NO_PRODUCER | an official-finding / attributed-response source policy |
| hearing_questions | published nomination + conflicting/gap inputs | none | derived | DERIVATION_ONLY or NOT_APPLICABLE | reviewed question artifact contract |
| forecast | `Hypothesis` (H0/H1/H2, falsifier) | contract exists, no writer | derived | DERIVATION_ONLY | reviewed scenario artifact with falsifier and horizon |

## Empty-section reasons

Each section carries a projection-only `reason` when it has no entry. It is computed from the
inputs the public projection already receives; no schema, enum table or review data is read.

| Reason | Meaning | Used for |
|---|---|---|
| `SOURCE_NOT_COLLECTED` | no official source supplying this section is linked to the Person | source-backed sections |
| `INSUFFICIENT_EVIDENCE` | published inputs exist below the comparison/analysis minimum | recent_changes, repeated_patterns |
| `DERIVATION_NOT_AVAILABLE` | inputs may suffice but no reviewed derived artifact exists | repeated_patterns, hearing_questions, forecast |
| `NOT_APPLICABLE` | canonical Claims show the lane does not apply (status `NOT_APPLICABLE`) | assembly_base_profile in the general path; hearing_questions without a published nomination |

The public projection sees only published Claims, so it cannot distinguish
`COLLECTED_NOT_LINKED`, `IDENTITY_REVIEW_REQUIRED` or `CLAIM_NOT_PUBLISHED`; those remain operator
review states and are deliberately not exposed. `NOT_APPLICABLE` is never inferred from a title
string, and none of these reasons asserts that a record does not exist.

## Source-attributed career periods

Both the Assembly and general Person path include current, published, evidence-backed career
Claims for the exact resolved Person and source contract:

| Predicate | Source contract | Date basis / attribution |
|---|---|---|
| `ASSEMBLY_BIOGRAPHY_CAREER` | `assembly_member_profile_biography` | normalized `period_start/end/point` and their DAY/MONTH/YEAR precision; `SOURCE_ATTRIBUTED_BIOGRAPHY` |
| `NEC_CANDIDATE_CAREER` | `nec_assembly_candidate_submission` | stated period qualifiers if present; otherwise undated candidate-submitted career/occupation; `CANDIDATE_SUBMITTED_CAREER` |
| `ASSEMBLY_HISTORICAL_TERM` | `assembly_historical_member_term` | exact `term_start/end`; historical party/district; `HISTORICAL_ASSEMBLY_TERM` |

The existing API's SourcePolicy/publication validation remains mandatory. The projection adds
no ingestion, identity resolution or publication authority. It independently excludes wrong
Person IDs, unresolved/superseded Persons, unpublished/superseded Claims, wrong source contracts
and entries without matching SUPPORT Evidence. Heading-only biography lines, including colon
variants such as `■ 경력:`, do not become events. A published UNKNOWN remains an unresolved,
non-asserted record; SUPPORT/REFUTE conflict and exact evidence/snapshot/observation IDs survive.

`ProfileEntry.details.career_period` is additive to the existing read DTO:

```text
start, end, point: ISO date | null
start_precision, end_precision, point_precision: DAY | MONTH | YEAR | UNKNOWN
ongoing: boolean (only an explicit source marker; not a present-day assertion)
```

`details.source_contract` and `details.career_semantics` identify the source meaning. Historical
terms additionally carry `historical_party`, `historical_district` and `term_name` when stated.
The entry title, Claim ID, epistemic status, `asserted_as_true`, evidence and source conflict
are preserved. Dates come only from source-specific period qualifiers, never `valid_from`,
`recorded_at`, the NEC election date or a roster capture. In particular, the current NEC
publisher supplies no parsed career period, so its career/occupation entries remain undated.

The legacy `entry.date` is populated only when the first stated boundary/point is DAY-precise.
Consumers must use `career_period` for coarse dates: `2024-01-01` with MONTH precision displays
as `2024.01`, not January 1. Do not use the relationship overlap helper for display: it moves
coarse bounds conservatively, whereas the timeline retains the source's stated units. Malformed
or reversed dates do not produce a fabricated interval; the attributed record remains visible.
Dated records sort before undated records deterministically. A former-only Person retains the
general profile and gains the historical timeline without a current-role or current-party claim.

## Disclosed responsibility

OpenDART executive-status filings carry a company-written `담당업무` (`responsibility`). For a
published, evidence-backed `OPENDART_DISCLOSED_EXECUTIVE_ROLE` Claim with a non-blank value, the
current-power section shows it verbatim as a source-attributed CLAIM
(`company_disclosed_responsibility_not_authority`). It keeps the role Claim's exact evidence trace
to its snapshot and observation. Authority is never derived from a title, an affiliation or a
nomination.
