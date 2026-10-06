# Person profile section producers

Audited on 2026-10-06 against master `dec4a53`. This is the canonical inventory of which upstream
producer feeds each Person profile section rendered by `packages/rendering/profile_projection.py`.
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

| Section | Renderer input | Current producer | Lane | State | Missing step |
|---|---|---|---|---|---|
| identity | Person | identity materialization | source | WORKING | — |
| gukgam_2026 / public_institution_roles / corporate_roles | `LISTED_AS_GUKGAM_WITNESS`, `ALIO_REVIEWED_PERSON_ROLE`, `OPENDART_DISCLOSED_EXECUTIVE_ROLE` | witness/OpenDART reviewed LINK_PERSON, ALIO source-context materialization | source | WORKING (rendered only when non-empty) | publication of the 2,688 ALIO role Claims is an owner decision |
| assembly_base_profile | Assembly roster Claims | Assembly roster feeder | source | NOT_APPLICABLE in this path by construction | — |
| summary / career_timeline | `NOMINATED_AS`, `APPOINTED_AS`, `HELD_ROLE`, `SERVED_AS`, … | Golden Set and `ReviewedPersonBundle` only | source | PARTIAL | no feeder emits these predicates for batch People; disclosure roles stay in their own source sections |
| recent_changes | dated historical `HELD_ROLE`/`APPOINTED_AS` with `change_input_scope` | Assembly historical reviewed packet + `SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1` | derived | PARTIAL | a second Person lane with two comparable dated Claims of the same dimension |
| current_power_tasks | `HAS_AUTHORITY`…`SUPERVISES`; OpenDART `responsibility` | reviewed fixtures; **OpenDART reviewed executive link (this change)** | source | PARTIAL | statute/organization-chart sources for public officials (BLOCKED_SOURCE) |
| appointment_logic | `APPOINTMENT_RATIONALE`, … | Golden supplement only | source (attributed text) | NO_PRODUCER | a reviewed official personnel-announcement lane quoting the stated rationale |
| decision_episodes | `DecisionEpisode` + published Claim + exact ClaimEvidence | Golden seed only (`seed_golden`) | source | NO_PRODUCER | an event lane (e.g. roll-call votes) materialized to Claims first; roll-call observations have no Claim path yet |
| repeated_patterns | ≥2 eligible episodes with independent origins | eligibility only (`validate_pattern`) | derived | DERIVATION_ONLY | decision episodes, then a reviewed pattern artifact |
| stakeholders | typed `Relationship` with ClaimEvidence refs, never `CO_MENTION` | Golden seed only | source | NO_PRODUCER | a typed relation producer; the ontology graph already shows Claim-backed role edges |
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

## Disclosed responsibility

OpenDART executive-status filings carry a company-written `담당업무` (`responsibility`). For a
published, evidence-backed `OPENDART_DISCLOSED_EXECUTIVE_ROLE` Claim with a non-blank value, the
current-power section shows it verbatim as a source-attributed CLAIM
(`company_disclosed_responsibility_not_authority`). It keeps the role Claim's exact evidence trace
to its snapshot and observation. Authority is never derived from a title, an affiliation or a
nomination.
