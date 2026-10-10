# Frontend direction — Evidence Encyclopedia

Status: ACCEPTED product direction, updated for the owner-directed 2026-10-08 discovery and
profile-restoration implementation. This describes intended behavior, not deployed coverage. Single canonical frontend
direction artifact; `DESIGN.md` remains the visual contract and
`docs/product/CIVIC_INTEL_NORTH_STAR.md` the product authority. Reference observations:
`docs/research/frontend-references/references-2026-10-04.json` (several reference pages were
blocked by robots/egress and are marked UNVERIFIED there).

## Product experience principles

1. Evidence underneath, curiosity on top: question → public record → Claim → Evidence → Source →
   method/limitation → independent judgment. Every visible fact reaches its evidence in one
   interaction.
2. Wiki-level navigability (fact box, in-page index, anchors), not wiki content culture.
3. Show dates, status and coverage beside the value; never hide UNKNOWN or conflict.
4. Available records lead. Missing eligible records have compact, precise coverage notes;
   unavailable capabilities never become teaser controls or zero-valued claims.
5. Presentation may group or sort; it never invents identity, relationship, position, witness
   status, wrongdoing, importance or influence.

## Reference matrix

| Reference | Pattern | Adopted | Civic implementation |
|---|---|---|---|
| Our World in Data | provenance metadata beside the data | Yes (primary) | Shared Evidence Panel field order |
| Wikidata | value + qualifiers + references | Yes | valid_from/valid_to + ClaimEvidence → Source rows |
| OpenSanctions/FtM | original vs normalized value; observed vs valid time; source vs canonical id | Yes | 원문 값 row; 기록 시각 vs 유효 기간; provider keys only in 감사 ID |
| TheyWorkForYou | record vs interpretation; reading guide | Yes (structure) | 근거 범위와 한계; no scores |
| OpenStates | identity header → activity → sources | Yes (structure) | Header + 핵심 기록 + sections + 출처 |
| OpenWatch | Korean field vocabulary; origin vs curated layer | Labels only | Fact-box labels; 처리 방식 row |
| Oligrapher/LittleSis | annotated bounded network | Concept only, deferred | Existing SVG ego view + list twin |
| Wikipedia/나무위키 | infobox, TOC, anchors | Navigation only | Fact box + profile index |

Rejected everywhere: ideology/alignment scores, party-deviation conclusions, risk/PEP badges,
co-occurrence edges, node size as influence, copied text/code/branding (GPL Oligrapher code,
CC BY-NC OpenSanctions data, unlicensed OpenWatch data).

## Page anatomy

**Home**: 모두의국감 / CIVIC INTELLIGENCE → one-sentence purpose and name search → BRIEF with
actual published audit-plan rows, plan/source dates and direct Claim links → EXPLORE using
working person, organization, party/committee filter and Gukgam paths → compact public coverage.
No arbitrary first-N people, inferred recommendations or unavailable CHANGE/MONEY cards.

**Person**: identity header (reviewed portrait only when eligible) → in-page index → 핵심 기록
fact box (value, status, 기준일, Claim anchor) → source-attributed CAREER / 경력 with real periods →
activity (including bounded bills/votes and eligible Gukgam context) → 공식 기록상 연결 → eligible
personal money and procedural records → compact coverage → Evidence/출처. Missing facet metadata
does not hide an otherwise public Person. Committee membership does not establish questioning.

**Organization**: header → index → 핵심 기록 (classification, executive-disclosure count labelled
집계, Gukgam target rows) → 2026 국정감사 (dates, committee, plan evidence, committee members) →
임원 (source-listed names, no Person linking) → money only when the MONEY contract is eligible →
연결 → 출처.

**Gukgam**: date index → date → committee → institution rows (FACT plan listing, plan page,
evidence link) → "감사 위원 N명 →" link to one committee-members section per committee →
source-listed witness/참고인 requests from published reviewed packets, with Person links only
where an exact reviewed identity link is publicly eligible. A request is not actual attendance.

## Evidence Panel

One shared component (`apps/web/app/components/evidence-panel.tsx`), native `<details>`,
anchor `#claim-{id}` opens it. Order: 기록 · 상태 (epistemic, publication when not PUBLISHED,
SOURCE CONFLICT) · 유효 기간 · 기록 시각 (Civic Intel recording time, not a real-world event) ·
근거 (stance + source) · 출처 (publisher, title/link, 공개일 or "공개일 미기재", 위치 = section/page,
확인 시각) · 원문 값 (as published qualifiers) · 처리 방식 · 출처 정책 · 한계 · 감사 ID (nested).

## Timeline

Use real temporal meaning from each published source contract: Gukgam plan dates, historical
Assembly terms and attributed biography/NEC career periods. Keep YEAR/MONTH/DAY precision and
FACT/CLAIM status. Undated public career statements remain visible as period-unspecified records.
Valid time, recorded time, source-observed time and supersession are labelled separately; fetch
time and election day are never substituted for a career start. Gaps are not interpolated.

## Graph

Bounded ego view, depth 1, typed evidenced edges only (SERVED_ON committee, HELD_ROLE, …), each
edge/list row linking to its Claim; list twin always rendered; uniform node size; no centrality.
Reuse the existing SVG + list for direct edges (Cytoscape remains admin-only). The existing
bounded `/relationships/people/{id}` projection may add typed Person–via–Person connections with
both sides' Claim/Evidence/Source, rule version and temporal overlap. Candidates default off;
UNKNOWN overlap does not establish shared tenure. Do not duplicate direct ontology facts, infer
friendship or use node size as influence. Frontend and D1 export/replay must share the same query.

## Status language

Use domain labels verbatim (FACT, CLAIM, INFERENCE, HYPOTHESIS, UNKNOWN, AVAILABLE, PARTIAL,
RESOLVED, REVIEW_REQUIRED, HARD_CONFLICT, SOURCE CONFLICT). No "verified/trusted/suspicious".
Colour never encodes political desirability; party is text, not colour.

## Responsive rules

390px: no horizontal overflow, long Korean names wrap, fact box stacks, evidence panel rows
stack label above value, graph degrades to the list, status chips ≥ 13px.

## Accessibility

Skip link, landmarks, semantic headings, visible focus, `<details>` disclosures for evidence,
labels not colour-only, list twin for every graph, ≥ 44px touch targets for navigation.

## Implementation boundary

Reuse the existing Evidence Panel, fact box, profile index, Gukgam contexts and published
legislative records. Restore the career producer and relationship consumer/export path as
coherent slices. Rights-approved portraits and personal-money publication remain separately
gated; absence never becomes an invented image or zero assets. Live, staged and blocked
milestone evidence belongs to the active execution plan, not this design document.

## Do not build

Rankings, ideology/corruption/influence scores, sentiment, engagement feeds, chatbot-first
navigation, whole-database graph, KPI dashboards, second data store, vector or graph DB,
reference-site content in the canonical DB.
