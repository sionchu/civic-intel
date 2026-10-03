# Frontend direction — encyclopedic record pages with evidence underneath

Status: PROPOSED 2026-10-04 (owner asked for a reference-backed direction; not yet an approved
release plan). Governs future public-surface work together with `DESIGN.md` and
`docs/product/CIVIC_INTEL_NORTH_STAR.md`; it does not override either.

## Decision in one line

Wiki-like *reading* structure (fast infobox → dated sections → footnotes), but every line is a
Claim with a status chip and a one-click evidence panel; the relationship network is a bounded,
typed ego graph with a table twin; "political orientation" is shown only as documented records;
news is a separately labelled discovery layer that never becomes evidence by itself.

## Reference assessment

| Reference | Borrow | Do not borrow |
|---|---|---|
| 나무위키 / Wikipedia | Infobox for a fast skim, TOC, per-sentence footnotes, dated career timeline | Free-text 논란/여담 sections, unsourced edits, editorial tone; CC BY-NC-SA text (never copy) |
| Wikidata | Statement + qualifiers (start/end) + references (URL, retrieved date) — maps 1:1 to Claim → Evidence → Source | Editor-filled "ideology/political position" fields |
| 열려라국회 (참여연대) | Member index filters (party, region, committee, terms); bills, committees, assets per member | Criminal-trial list (needs its own legal/source review) |
| OpenWatch / 뉴스타파 재산·후원금 | Dataset-level origin naming; year-by-year asset tables linked to 관보 | Wealth rankings ("랭킹"), wrongdoing-framed collections; unclear licences |
| TheyWorkForYou (BSD-3) | Votes grouped by policy area with drill-down to each division; published caveats | 0–100 policy scores rewritten as "consistently voted for" |
| GovTrack ideology | Openly published method | The score: cosponsorship PCA, ignores bill content and party; axis direction is data-derived |
| OpenSanctions / FollowTheMoney | Statement-level provenance (first/last seen, original value); relationships as typed entities with dates | PEP/"risk" framing; CC BY-NC data |
| LittleSis / Oligrapher (GPL-3.0) | Sourced, typed edges; annotated step-through maps | "Power network/who knows who" framing; GPL code |
| Our World in Data | "Sources and processing" tab, "what you should know", last/next update, citation, download | — |
| 빅카인즈 관계도 | Entity extraction as discovery only | Co-occurrence edges (forbidden: co-occurrence is not a relationship) |

Sources: watch.peoplepower21.org · docs.openwatch.kr/data/national-assembly ·
jaesan.newstapa.org/about · theyworkforyou.com/voting-information ·
govtracknews.wordpress.com/2010/12/26/repstats · opensanctions.org/docs/statements ·
github.com/public-accountability/oligrapher · ourworldindata.org · bigkinds.or.kr (checked 2026-10-04).

## Page anatomy

**Person**: header (name, current office, party *as of date*, last verified) → fact box with
status chip + footnote per row → office/party timeline (gaps rendered as UNKNOWN, never
interpolated) → committees/roles → legislative record (sponsored/cosponsored bills, votes by
topic; counts, not performance percentages) → assets/political funds by year (only when the
source lane is live) → documented relationships (ego graph + table) → 국감 appearances →
news (discovery layer) → sources and change history.

**Organization**: header (legal name, type, parent, legal basis) → fact box → governance
(heads/board with dated appointment sources) → money (existing MONEY contract) → 국감 targets and
records → documented relationships → news → sources and change history.

Sections without a live, eligible source lane are not rendered (missing capability beats
misleading capability).

## Network

- Ego graph only; depth 1 by default, depth 2 on explicit expand; ≤ ~50 nodes / ~100 edges with a
  visible "+N more (table)" note.
- Edges only from typed, evidenced relations (`HELD_ROLE`, committee membership, appointment,
  board role, bill cosponsorship, official donation record). Each edge carries period, status and
  evidence IDs; clicking opens the evidence panel. No name-only nodes, no co-occurrence edges.
- Style encodes type and status (dashed = CLAIM, conflict outline = SOURCE CONFLICT). Node size
  never encodes influence; no centrality metrics.
- Always render the accessible table twin.
- Library: keep `cytoscape` (already a dependency, used in the operator graph) via a client
  component with dynamic import; deterministic `concentric`/`breadthfirst` layouts.

## Political orientation

Default: no orientation label. Show documented facts only — party membership history with dates,
caucus/committee roles, sponsored bills, roll-call votes, the person's own published pledges as
attributed CLAIMs. A derived indicator follows the North Star rule: separate Analysis area,
MODEL-DERIVED label, published method/inputs/period/missingness/uncertainty, "왜 이 위치인가?"
drill-down, never on the main profile and never a single left/right score.

## News

Separate tab labelled "보도 (맥락)". Items link to records only through reviewed links. An
article may be the Source of an attributed CLAIM ("X 보도에 따르면 …") but is never promoted to
FACT automatically. Headline, outlet, date and outbound link only — no full text.

## Evidence panel

Footnote markers open a side panel: Claim text + status; Evidence value with original value;
Source (publisher, document/API locator, URL, retrieved/observed time, licence); method; and
for SOURCE CONFLICT every competing value side by side. Offer "cite" and "download record".

## Implementation order (post-launch)

1. Evidence side panel shared by Person, Organization and 국감 rows.
2. Person/Organization fact box + timeline over existing Claims.
3. Cytoscape ego graph with table twin over the existing ontology projection.
4. Legislative record and news layer only after their source lanes pass SourcePolicy gates.
