# Identity Resolution

## Purpose

Civic Intel must resolve a person before combining evidence into one profile. Cross-lane career
movement makes this stricter than ordinary same-record matching because a real person can move
between different organizations and offices over time.

```text
company executive
 -> presidential adviser
 -> commission member
```

Different role text is therefore not automatically an identity conflict.

## Two resolution contexts

### Existing local/same-state resolver

`packages.verification.identity.resolve_identity()` remains the conservative V0 resolver for
candidate comparisons where current office/organization agreement is useful evidence.

Issue #39 does not weaken or silently reinterpret that function.

### Cross-lane resolver

`resolve_cross_lane_identity()` is used only when the system is deciding whether candidates
from different career/source lanes may belong to one Person.

Rules:

- name/alias overlap is required;
- name-only never resolves;
- different office/organization is neutral;
- hard birth-date conflict fails closed;
- explicit source-backed bridge evidence is required for `RESOLVED`;
- only `RESOLVED` candidates may later become one Person/profile projection.

## Allowed bridge evidence

### `EXACT_BIRTH_DATE`

Both candidates expose the same exact birth date and the evidence keeps the public source
reference that supports the date linkage.

A missing date cannot be replaced by guessing year/month/day precision.

### `EXTERNAL_ID`

A reviewed public source/crosswalk demonstrates the same stable identifier in the same
namespace on both sides.

Different identifier namespaces are not interchangeable merely because values look similar.

### `OFFICIAL_CAREER_CONTINUITY`

An official personnel/appointment source explicitly links a named person's prior public or
professional role to the new role.

Example semantics:

```text
official personnel briefing:
A, previously company X CTO, is appointed/designated/nominated to role Y
```

This can establish identity continuity. It does **not** automatically make every detail of the
prior career independently verified; the original company/public source is still needed for
that CareerEpisode's final FACT status.

### `OFFICIAL_BIOGRAPHY_CONTINUITY`

An official biography explicitly presents two career episodes as belonging to the same person.
The biography source is retained as identity evidence and important underlying career facts are
verified from their primary source families where practical.

## Evidence that is never sufficient

Cross-lane identity cannot be resolved from:

- same name alone;
- co-mention in news;
- appearing at the same event;
- social or organizational proximity;
- political faction/party assumptions;
- inferred friendship/loyalty;
- overlapping topics or policy positions;
- analyst intuition without a source reference.

Those signals may be useful for discovery in other contexts but are not identity evidence.

## Scoring boundary

The score is an internal deterministic decision aid, not a public confidence percentage.

- base name/alias overlap: review-level only;
- each evidence type has one bounded contribution;
- multiple records of the same evidence type do not repeatedly inflate the score;
- birth-date conflicts override positive continuity evidence.

The public system should expose the decision status and underlying sources rather than convert
this score into a probability.

## Profile integration

```text
Feeder candidate A
Feeder candidate B
 + CrossLaneIdentityEvidence
 -> CrossLaneIdentityDecision
    -> RESOLVED
       -> ProfileResearchTarget
       -> public-official-profiler
    -> REVIEW / UNRESOLVED
       -> separate candidates; no silent merge
```

### `ProfileResearchTarget`

`packages.verification.profile_target.build_profile_research_target()` is the review-only
bridge between identity resolution and profiling.

The target:

- keeps one primary feeder observation;
- accepts additional observations only when each cross-lane decision is `RESOLVED`;
- preserves every observation's original lane, office, organization, career anchors and
  source references;
- deduplicates aggregate source references without erasing observation-level provenance;
- carries discovery reasons and appointment-target slugs only as research context;
- never creates a Person DB merge, publishable FACT or appointment probability by itself.

A same-name observation with no bridge evidence, a birth-date conflict, or any `REVIEW` /
`UNRESOLVED` decision cannot enter the target.

The profiler then consumes this target as structured research context and must still create
canonical Claim/Evidence/Source records before anything becomes publishable.

### Reviewed Person onboarding

A `ProfileResearchTarget` does not write to the canonical database by itself. A new Person may
enter the canonical SQLAlchemy store only through an explicit `ReviewedPersonBundle` and
`SqlAlchemyRepository.import_reviewed_person()` transaction.

The import gate:

- requires a `RESOLVED` Person whose canonical name matches the research target;
- refuses existing Person IDs and record-ID collisions rather than silently upserting;
- permits references to existing canonical Source/SourcePolicy records but does not redeclare
  conflicting copies;
- verifies SourcePolicy storage rights before writing new source/snapshot metadata;
- validates every published claim through the existing publication gate before commit;
- rolls back the complete transaction on any identity, reference, policy or publication failure.

Discovery reason, talent-pool inclusion and appointment-target relevance remain research context
only and never become publishable claims through onboarding.
