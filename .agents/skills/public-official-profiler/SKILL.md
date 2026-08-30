# Public official profiler

Use structured evidence as the system of record. Resolve identity before an
identity-specific profile, enforce SourcePolicy before processing, store atomic claims,
deduplicate source origins, retain uncertainty labels, and refuse publication when any
traceability or quality gate fails.

## Preferred structured input

Prefer a resolved `ProfileResearchTarget` when a person was discovered through one or more
career feeders.

```text
feeder observations
 -> source-backed cross-lane identity resolution
 -> ProfileResearchTarget
 -> profiler research
 -> Claim / ClaimEvidence / Source / SourcePolicy
 -> reviewed ProfileSnapshot
```

A `ProfileResearchTarget` is a research instruction, not a second Person truth store. It may
contain several historical offices and organizations because career movement is expected.
Only observations accepted by the cross-lane identity gate may be treated as belonging to the
same research target.

## Reuse before rediscovery

Before searching for the same fact again, inspect the target's feeder observations, source
lanes, source references and identity evidence. Reuse validated structured material where
appropriate, but preserve its original semantics.

Examples:

- a Presidential personnel briefing can establish the exact public personnel action;
- a company official profile can establish that the company publicly identified the person in
  a senior role;
- an OpenDART row can establish what the reporting company disclosed in that filing;
- an NKIS row can establish the named responsible researcher for that output;
- a candidate-submitted NEC career field establishes what the candidate reported to NEC.

These attributed source facts are not automatically independent verification of every prior
career statement. Important prior CareerEpisodes must be checked against the strongest
available original source before promotion to independent `FACT`.

## Discovery is not appointment evidence

A feeder discovery reason, talent-pool inclusion or `AppointmentTarget` relevance explains why
the person is worth researching. It does not prove that the President, government, party or
appointing authority is actually considering that person.

Actual consideration requires a separate attributable `CLAIM` or official `FACT`.
Never generate appointment probability, faction, loyalty or hidden-influence scores from the
research target.

## Profile output rules

The profiler should build the evidence-backed profile from the canonical graph rather than
copying the target object directly into publication.

- preserve `FACT / CLAIM / INFERENCE / HYPOTHESIS / UNKNOWN / ENTITY_UNRESOLVED`;
- preserve support and refutation together;
- keep time-bounded CareerEpisodes rather than flattening a person's career to one occupation;
- retain limitations and unresolved identity/source gaps;
- patterns still require at least two independent decision episodes;
- relationships still require typed evidence, not co-mention or proximity;
- publication still requires Claim -> ClaimEvidence -> Source -> SourcePolicy traceability.
