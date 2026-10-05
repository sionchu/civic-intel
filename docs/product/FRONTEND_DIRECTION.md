# Frontend direction — Evidence Encyclopedia

Status: ACCEPTED for the public beta on 2026-10-04 (owner-directed). Single canonical frontend
direction artifact; `DESIGN.md` remains the visual contract and
`docs/product/CIVIC_INTEL_NORTH_STAR.md` the product authority. Reference observations:
`docs/research/frontend-references/references-2026-10-04.json` (second pass the same day verified
the OpenStates person template and Oligrapher licence; TheyWorkForYou MP pages and Wikidata help
pages remain BLOCKED and are marked so there).

## Product experience principles

1. Evidence underneath, curiosity on top: question → public record → Claim → Evidence → Source →
   method/limitation → independent judgment. Every visible fact reaches its evidence in one
   interaction.
2. Wiki-level navigability (fact box, in-page index, anchors), not wiki content culture.
3. Show dates, status and coverage beside the value; never hide UNKNOWN or conflict.
4. Missing capability is shown as a precise unavailable lane, never as an empty promise.
5. Presentation may group or sort; it never invents identity, relationship, position, witness
   status, wrongdoing, importance or influence.

## Reference matrix

| Reference | Pattern | Adopted | Civic implementation |
|---|---|---|---|
| Our World in Data | provenance metadata beside the data | Yes (primary) | Shared Evidence Panel field order |
| Wikidata | value + qualifiers + references | Yes | valid_from/valid_to + ClaimEvidence → Source rows |
| OpenSanctions/FtM | original vs normalized value; observed vs valid time; source vs canonical id | Yes | 원문 값 row; 기록 시각 vs 유효 기간; provider keys only in 감사 ID |
| TheyWorkForYou | record vs interpretation; methodology beside summaries | Structure only | 근거 범위와 한계, 자료 범위 lanes; its agreement-score phrase scale is rejected |
| OpenStates (MIT, template verified) | identity header → bills → votes → sources; "former" status | Yes (structure) | RecordHeader + 핵심 기록 + sections + 출처; per-Claim sourcing instead of its page-level source list |
| OpenWatch | Korean field vocabulary; origin vs curated layer | Labels only | Fact-box labels; 처리 방식 row |
| Oligrapher/LittleSis | annotated bounded network | Concept only, deferred | Existing SVG ego view + list twin |
| Wikipedia/나무위키 | infobox, TOC, anchors | Navigation only | Fact box + profile index |

Rejected everywhere: ideology/alignment scores, party-deviation conclusions, risk/PEP badges,
co-occurrence edges, node size as influence, copied text/code/branding (GPL Oligrapher code,
CC BY-NC OpenSanctions data, unlicensed OpenWatch data).

## Page anatomy

**Home**: short plain introduction (no slogan hero) → the record path line (Identity → 공개 기록 →
Claim → Evidence → Source) → 국감 2026 next official audit date with committee → institution links
and the "not a complete target list" note → 기록 찾기 rows (people, organizations, Gukgam) with
published counts as small coverage text.

**Person**: RecordHeader (name, identity status, 공개 Claim/출처 counts, 최근 기록 반영 labelled as
Civic Intel recording time) → in-page index → 핵심 기록 fact box (label, value,
status, 기준일, 근거 anchor) → 2026 국정감사 (only for members of a Gukgam committee: committee,
audit dates, audited-institution count, "membership ≠ questioning" note) → 기록 sections with
Evidence Panels → one "아직 수집되지 않은 기록" line for non-live lanes → 공식 기록상 연결
(ego view + list) → 출처.

**Organization**: RecordHeader → index → 핵심 기록 (classification, executive-disclosure count labelled
집계, Gukgam target rows) → 2026 국정감사 (dates, committee, plan evidence, committee members) →
임원 (source-listed names, no Person linking) → money only when the MONEY contract is eligible →
연결 → 출처.

**Gukgam**: compact header with in-page links → scope (counts, committees, plan dates, today) →
sticky date index → one collapsed `<details>` per audit day (today/next open; `#audit-{date}` opens
the named day) → committee → institution rows (FACT, plan page, one Claim/Evidence link; audit IDs
live in the destination Evidence Panel, not per row) → "감사 위원 N명 →" or "공개된 위원 명부 Claim
없음" → committee-members section → search → 자료 범위 lanes (plan PARTIAL, members AVAILABLE,
witnesses UNKNOWN, Q&A UNKNOWN), computed from the read result. Witnesses only after the witness
lane publishes real reviewed packets.

## Evidence Panel

One shared component (`apps/web/app/components/evidence-panel.tsx`), native `<details>`,
anchor `#claim-{id}` opens it. Order: 기록 · 상태 (epistemic, publication when not PUBLISHED,
SOURCE CONFLICT) · 유효 기간 · 기록 시각 (Civic Intel recording time, not a real-world event) ·
근거 (stance + source) · 출처 (publisher, title/link, 공개일 or "공개일 미기재", 위치 = section/page,
확인 시각) · 원문 값 (as published qualifiers) · 처리 방식 · 출처 정책 · 한계 · 감사 ID (nested).

## Timeline

Only for real temporal meaning. Today that is the Gukgam plan dates. Person role timelines stay
unrendered until historical-role sources exist (current data has a single roster snapshot).
Valid time, recorded time, source-observed time and supersession are labelled separately; fetch
time is never shown as an event; gaps are not interpolated.

## Graph

Bounded ego view, depth 1, typed evidenced edges only (SERVED_ON committee, HELD_ROLE, …), each
edge/list row linking to its Claim; list twin always rendered; uniform node size; no centrality.
The public view stays the existing SVG + list (Cytoscape remains admin-only) until depth-2 or
annotation steps are needed.

## Status language

Use domain labels verbatim (FACT, CLAIM, INFERENCE, HYPOTHESIS, UNKNOWN, AVAILABLE, PARTIAL,
RESOLVED, REVIEW_REQUIRED, HARD_CONFLICT, SOURCE CONFLICT). No "verified/trusted/suspicious".
Colour never encodes political desirability; party is text, not colour.

## Responsive rules

390px: no horizontal overflow, long Korean names wrap, fact box stacks, evidence panel rows
stack label above value, graph degrades to the list, status chips ≥ 11px.

## Accessibility

Skip link, landmarks, semantic headings, visible focus, `<details>` disclosures for evidence,
labels not colour-only, list twin for every graph, ≥ 44px touch targets for navigation.

## Implementation order

1. Evidence Panel + anchors (done 2026-10-04).
2. Fact box + in-page index (done 2026-10-04).
3. Gukgam context: committee members (done), person ↔ Gukgam (done), executives as source-listed
   names (done).
4. Reading-first pass (done 2026-10-04, second slice): Korean fact labels via `claim-labels.ts`,
   shared RecordHeader with coverage/recording time, compact limitation list, Gukgam day
   disclosures (mobile page 47.8k px → 8.1k px on the 177-row preview, sub-24px targets 177 → 0),
   Home re-centred on the next audit date, decorative clichés removed from CSS.
5. Directory usability (done 2026-10-04): People/Organizations draw 60 rows per page with
   "더 보기"; Organizations gains a name and ALIO classification filter (preview mobile
   33.9k px → 13.3k px); decorative row numbers removed; sub-24px touch targets on Home and
   profiles fixed.
6. Gukgam payload: move the search roster to a lighter read (open).
7. Legislative/news layers only after their source lanes pass SourcePolicy gates.

## Do not build

Rankings, ideology/corruption/influence scores, sentiment, engagement feeds, chatbot-first
navigation, whole-database graph, KPI dashboards, second data store, vector or graph DB,
reference-site content in the canonical DB.
