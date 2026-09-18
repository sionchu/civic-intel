# Reviewed Cross-Lane Person Packet — Kim Dong-cheol v1

Status: COMPLETE — reviewed packet and source bridge verified; no canonical persistence (2026-09-19).

## Objective and boundary

Create exactly one research-only cross-lane identity packet for 김동철 from the already-published
ALIO Item 4 executive observation and the official National Assembly historical profile, using the
official KEPCO biography as the explicit identity-continuity bridge. This work does not create,
merge, supersede or link a canonical Person, publish a Claim, rerun acquisition, write staging or
add a feeder.

The intended research decision is `IdentityStatus.RESOLVED` with
`IdentityDecisionClass.OFFICIAL_CAREER_CONTINUITY`, admitted only to the existing
`ProfileResearchTarget` path.

## Source and identity evidence

The current public ALIO Organization page for 한국전력공사 shows the existing Organization record,
the 김동철 `상임기관장` / `사장` executive row, term `2023-09-19 — 2026-09-18`, one Evidence
trace, and the exact canonical trace:

```text
Organization  3ef4de75-fa3f-5815-81f4-8bc5efdc33f1
Claim         ce471401-3d17-552d-b7c4-627ffaa97dd2
Evidence      931d8c05-2e3d-5cf2-bac2-1e2af884bb51
Snapshot      1883de13-d245-4aec-95f6-8153fccc442f
Observation   b7df9687-f7aa-4a9b-80fc-acc3f1655ed3
Source        4e3ca86f-52c9-4316-ac1a-0f09449e5b5c
Predicate     ALIO_CURRENT_EXECUTIVE_DISCLOSURE
```

The preserved staging publication receipt reports zero Person links for the activated ALIO
executive Claims. The public page keeps this executive in the Organization evidence path and does
not expose a Person link. No provider-record key or raw normalized observation is copied into the
packet.

The official KEPCO board page
`https://www.kepco.co.kr/home/esg/governance/directors/composition/conts.do` directly presents
`사장 김동철 (金東喆)`, the term `23.09.19 ~ 26.09.18`, and the prior role
`前) 국회 제17ㆍ18ㆍ19ㆍ20대 국회의원` in the same official biography. It also reports
`1955.06.30`; this is corroborating metadata only and is not the decision driver.

The official National Assembly page
`https://www.assembly.go.kr/members/20th/KIMDONGCHEOL` presents 김동철, `金東喆`,
`KIM DONGCHEOL`, `1955-06-30`, four terms (`17, 18, 19, 20`) and official member code
`DCR84445`. The Assembly role remains independently supported by this source. Page fulltext and
contact details are not retained.

## Decision contract

- Same-name candidates without the KEPCO continuity evidence remain `REVIEW` /
  `CONTEXT_REVIEW`.
- The KEPCO source is represented as
  `CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY` with
  `from_role=국회 제17·18·19·20대 국회의원` and `to_role=한국전력공사 사장`.
- With that bridge, `resolve_cross_lane_identity()` returns `RESOLVED` /
  `OFFICIAL_CAREER_CONTINUITY`.
- Changing one candidate name returns `UNRESOLVED` / `NAME_CONFLICT`.
- The Assembly birth date corroborates the two official source profiles but does not become an
  ALIO feeder field or an `EXACT_BIRTH_DATE` primary decision.
- Party, faction, co-mention, organizational proximity, topic overlap and analyst intuition are
  not identity evidence.

## Packet and ProfileResearchTarget

The bounded fixture is
`tests/fixtures/reviewed_cross_lane_kim_dongcheol_001.json`. It preserves both source lanes,
the ALIO canonical trace, official source references, the official bridge, and the expected
research decision. It is not a generic packet registry.

The regression builds a primary `ALIO_ITEM4_EXECUTIVE` observation and a linked
`NATIONAL_ASSEMBLY_HISTORICAL_REVIEW` observation through the existing
`build_profile_research_target()` function. It preserves lane, office, organization, career
anchor and source-reference provenance, while retaining `RESEARCH_IDENTITY_ONLY` semantics.
The disposable repository assertion remains empty: no Person, PersonObservationLink or Claim is
created, and `import_reviewed_person()` is not called.

No canonical Person materialization, merge, supersession or staging operation follows this PASS.

## Verification

- Official KEPCO, National Assembly and public staging pages were read-only checked on 2026-09-19.
- Targeted identity/profile tests pass: `tests/test_cross_lane_identity.py` and
  `tests/test_profile_research_target.py` — 22 passed.
- Expected production-code diff: none; schema and dependencies remain unchanged.
- Full repository verification passes: `pytest` 376 passed, 1 skipped; Ruff; mypy; Golden quality;
  Web lint, typecheck, UI tests (11/11), production build and standalone contract check. Markdown
  relative-link validation checked 69 links, and `git diff --check` passed.
- GitHub Verify and final commit/push parity are the remaining repository closure gates.

## Closure marker

Emit `REVIEWED_CROSS_LANE_PERSON_PACKET_KIM_DONGCHEOL — PASS` only after the source checks,
negative controls, ProfileResearchTarget proof, full verification and GitHub Verify all pass.

## Next concrete action

Run a read-only canonical Person collision/materialization preflight for 김동철: search existing
People, inspect same-name and birth-date conflicts, and choose only among `LINK_EXISTING`,
`REVIEWED_ONBOARD` or `KEEP_RESEARCH_ONLY`; perform no write.
