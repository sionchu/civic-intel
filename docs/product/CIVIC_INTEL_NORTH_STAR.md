# Civic Intel North Star

## Authority and current scope

This document is the canonical long-term product direction and Derived Intelligence boundary.
[Architecture](../../ARCHITECTURE.md) governs executable boundaries;
[V0 scope](V0_SCOPE.md) governs current delivery; [DESIGN.md](../../DESIGN.md) remains the
current visual contract. Future features here require their own scoped execution plans and
source gates. This document neither changes those contracts nor authorizes their implementation.

Baseline inspected on 2026-09-14: remote master `0ad72f6331a82fd0b46be232a5945c12ceba30e5`.
The organization-scoped Claim/Evidence extension is the bounded follow-on slice recorded in this
revision; it does not authorize a live ALIO organization binding or public MONEY route.
A local running capture, observation count or passing test does not establish shipped product
coverage, public publication or production deployment.

| Status | Capability |
|---|---|
| CURRENT | Evidence Core architectural direction: canonical contracts, shared SQLAlchemy persistence, SourcePolicy, snapshots, observations, deterministic materialization and publication validation |
| CURRENT | Read-only Evidence Directory, profile/evidence projection and REST routes; internal review is opt-in, not an authenticated public operator system |
| CURRENT | Canonical Claim/Evidence supports exactly one Person or current Organization subject; read-only organization Claim reads preserve the shared provenance path |
| PLANNED | General Derived Intelligence, issue experience, policy-position models, influence metrics, recommendations and community |
| PLANNED | Broader public API distribution, licensed bulk/change feeds and read-only MCP agent access |
| NOT IMPLEMENTED AS PRODUCT CAPABILITIES | Asset, roll-call vote and public MONEY derived publication; local proposer candidate as a shipped feature; community, MCP and intelligence algorithms |

Existing `AssetDisclosure`/`AssetItem` contracts and an assets route do not constitute a working
asset ingestion product. Existing source-conflict projection, hypotheses and temporal contracts
do not constitute a general analytics platform. CURRENT describes repository implementation,
not deployment or complete live data acquisition. The bounded ALIO Item 12 observation and
in-memory MONEY calculation are source-specific evidence work, not a public MONEY product. The
organization-level Claim/Evidence capability now exists as a canonical-row-gated contract, while
live ALIO organization binding and the public MONEY projection remain separate follow-on work.

## Purpose

Civic Intel is an evidence-backed public governance intelligence platform that helps people
examine public figures, institutions, actions, money, decisions, and change through verifiable
public records rather than relying only on partisan labels, headlines, or engagement-driven
recommendation algorithms.

Civic Intel은 인물·기관·행동·돈·결정·변화를 공개 기록으로 살펴보는 공공 거버넌스
인텔리전스 플랫폼이다. 사람은 흥미로운 질문에서 출발해 근거와 맥락을 읽고 스스로
판단할 수 있어야 한다. 인명록과 정부 데이터 복제는 그 목적을 위한 일부 수단이다.

Evidence underneath. Curiosity on top.

The experience should be compelling and quick to understand: recent changes, unexpected
comparisons, public-money changes, conflicting records, behavior differing from a party average,
appointments and issue-specific actions. Strong FACTs deserve clear presentation. Official
audit, judgment, disciplinary, investigation and indictment statuses may be stated precisely.
Evidence and published methodology support strong analysis and presentation; restraint does
not require silence or equal weight for unequal evidence.

## Three product layers

### 1. Evidence Core — current architectural foundation

The source-processing path remains:

```text
SourcePolicy → Source → SourceSnapshot → FeederObservation
→ deterministic identity/materialization → Person or supported canonical object
→ Claim + ClaimEvidence → publication gate
```

This is a dependency description, not permission to materialize every observation. Reviewed
manual records may lack a feeder observation. Every rendered factual item retains the existing
`Claim → ClaimEvidence → Source → SourcePolicy` trace, with exact snapshot/observation references
where applicable. SourceRun and SourceCheckpoint describe operations, not truth.

Canonical identity, source-backed claims, FACT publication, provenance, temporal validity and
corrections are decided through existing Core contracts and gates. Visibility and truth remain
separate: published UNKNOWN stays non-asserted. FACT, CLAIM and UNKNOWN retain their existing
semantics. AI, community and rankings cannot merge identities, overwrite records or publish
through a side door. SourceSnapshot remains the sole canonical source capture; observations
are immutable and policy-minimized. Deterministic identity never becomes name-only linking.

### 2. Derived Intelligence — planned analysis layer

Derived Intelligence comprises reproducible computations over eligible Evidence Core inputs:
changes, comparisons, activity networks, public-money analysis, policy positions, vote similarity,
party deviation, repeated patterns, unusual changes, source conflicts and temporal patterns.
An analysis is not a canonical FACT merely because its inputs contain FACTs.

Every published result must explain:

- methodology and calculation or model version;
- exact input scope, supporting canonical IDs or reproducible query scope pinned to an as-of
  snapshot/version, including publication and epistemic eligibility;
- time range, units, comparison cohort, denominator and missingness;
- source coverage and limitations, including uncertainty for model outputs;
- how corrected, withdrawn or superseded inputs affect the result.

Reruns must be reproducible against pinned inputs. Input correction requires a traceable revised
result or withdrawal, not silent reuse of an old conclusion. Incomplete coverage cannot imply
zero activity, and different observation counts cannot establish different performance without
comparable scope. Source conflicts retain supporting and refuting evidence and origin independence.
Co-occurrence and correlation do not establish causation, private influence or friendship.

`DERIVED`, `MODEL-DERIVED` and `COMMUNITY` below are product concepts, not additions to
`EpistemicStatus`, persistent models or API enums. Any future implementation must first map its
semantics to the existing contracts and propose only the smallest justified extension.

### 3. Public/Product Experience — current directory, planned richer surfaces

Headlines, cards, rankings, comparisons, issue pages, trends, alerts, visual maps and interactive
analysis may create curiosity. They must retain the distinction between official record, computed
analysis and user opinion, visible beside the result rather than buried in a disclaimer.
For example: an accurately scoped court outcome with its FACT status; party-average vote
distance as DERIVED; a user's interpretation as COMMUNITY. A pending case is not a final judgment.

Drill-down must expose Claim, Evidence, Source, SourcePolicy and applicable SourceSnapshot /
Observation, plus Methodology, Coverage and Limitations for analysis. Access respects source
rights and privacy; traceability does not require publishing prohibited raw payloads. Current
DESIGN.md remains binding until an approved future UI milestone updates it.

## Five discovery primitives

| Primitive | Reader question | Candidate experiences | Required interpretation |
|---|---|---|---|
| CHANGE | 무엇이 바뀌었는가? | Role, party, asset, business-expense or vote-pattern changes; institution moves; source corrections | Distinguish event/valid time, capture time and correction; capture churn alone is not a real-world change |
| CONTRADICTION | 무엇이 서로 맞지 않는가? | Conflicting official sources, past/current records, public statement versus official action | Preserve date, context and comparable propositions; mismatch is not automatically lying, hypocrisy or corruption |
| COMPARISON | 누구와 어떻게 다른가? | Party, same-role, prior-year, peer-institution and same-issue comparisons | Declare cohort, period, units, denominators and missing coverage |
| CONNECTION | 공식 기록상 어떤 접점이 존재하는가? | Co-sponsorship, committees, employment, appointments/recommendations, boards and official joint activity | Typed, dated, evidenced contact; proximity is not friendship or influence |
| MONEY | 공적 자금과 금전적 공시가 어떻게 변했는가? | Business expenses, disclosed assets, executive compensation, political funds and contribution aggregates | Retain disclosure/valuation period, units and ownership scope; money alone is not wrongdoing |

These are discovery vocabulary, not five new tables or implemented feeds. Money surfaces retain
the existing prohibition on private-family discovery, precise residences and ordinary donor
discovery. Aggregate contributions do not authorize materializing donors as Persons.

## Policy profiles, evidence asymmetry and recommendations

The long-term goal is a multi-dimensional, behavior-based policy profile: economy/markets,
welfare/redistribution, labor, society/culture, foreign affairs/security, environment/energy,
government role and regulation. Dimensions require official votes, sponsorship, committee work,
policy action or appropriately sourced official statements. A fixed left/right ideology score
is not the starting model. Observable alignment does not establish private belief.

A future model is visibly MODEL-DERIVED, with model version, input universe, period, missingness,
uncertainty and methodology. “왜 이 위치인가?” must reveal the underlying evidence. Dimensions,
classification choices and aggregation rules must be reviewable rather than hiding value choices
inside an opaque score.

Avoid false balance. Relevant evidence receives weight according to quality, independence,
scope and directness, not a quota for left/right positions. When records support one proposition
more strongly, show that asymmetry with the relevant counterevidence and limitations. A government
statement is attributable evidence, not automatically independent confirmation of its contents.

Recommendation defaults should use explicitly followed issues, institutions, regions, people,
policy fields and topics. Inferring political orientation from clicks and reinforcing that
orientation is not a product objective. Future ranking may combine relevance, recency, public
significance, evidence quality, meaningful novelty and useful evidence/viewpoint diversity.
Explain why an item is recommended and make explicit follows adjustable. Diversity does not mean
equal weight for unsupported claims. Engagement is useful feedback, but outrage and tribal
reinforcement must not become the sole optimization target. The five primitives supply curiosity.

## Evidence requirements for strong language

Terms are governed by their support and attribution, not blanket word bans.

| Term | Requirement |
|---|---|
| 비리 / 위법 / 부당 / 징계 | Attribute the exact supported official finding or procedural action, with date, authority, subject and current status. “감사원이 부당 집행으로 지적”, “법원이 유죄 확정”, and “검찰이 기소” describe different things. Investigation or indictment establishes that procedural event or allegation, not guilt; appeal, reversal and later correction remain visible |
| 낭비 | Use an attributed official finding or an explicit objective methodology whose scope supports the characterization. A methodology-based assessment stays DERIVED. An increase alone supports “지출 증가”; a comparable cohort may support “동종기관 상위”; repeated records may support “반복집행”. An anomaly is a signal, not proof |
| 영향력 | Prefer separate observable dimensions: formal power, legislative reach, committee authority, network centrality and appointment/governance reach. Publish definitions and scope; network centrality is not actual informal power |
| 친분 | A claim of friendship needs direct attributable evidence supporting that relationship and the normal relationship/publication gates. Do not infer an inner relationship from proximity; otherwise label only the documented joint activity, committee, employment or appointment connection |
| 정치성향 | Do not declare private beliefs as FACT. Attributed self-description retains attribution; behavior-based policy profiles, vote alignment and sponsorship patterns are Derived Intelligence |

Presentation strength must track the strength and precise object of the evidence. Neither an
official source nor an analyst's calculation licenses a broader accusation than it supports.

## Issue experience and community

PLANNED `/issues/{issue}` connects a current event, historical context, actual actions and official
sources. Candidate sections are why this matters now, key facts, bills/policies, official actions,
actual evidence for competing positions, people, votes/sponsorship, public-money effects, recent
changes, source conflicts and evidence. Issue selection and scope must be explained. This route
is a product concept, not an existing endpoint or a mandate to copy news headlines.

PLANNED community supports evidence-aware discussion through OPINION, COUNTERPOINT,
ADD_EVIDENCE, CORRECTION and CONTEXT intents. Evidence-bearing comments may attach a Source
link or canonical evidence reference. Helpful, evidence-backed, informative and fact-check-needed
signals may supplement likes; votes never decide factual validity. A submitted source or correction
must pass the normal acquisition, identity and publication process before affecting the Core.
Community opinion never automatically becomes a canonical Claim or FACT.

Brigading, harassment, spam and unsupported defamatory allegations require a separate future
operator/moderation design, including access and review responsibilities, before community launch.
No social tables or moderation implementation are authorized here.

## Public infrastructure and sustainable service

The current read-only REST API is a foundation. Long-term distribution serves citizens, journalists,
researchers, civic organizations, developers, newsrooms, AI agents and fact-checking tools through
Web, REST API, bulk/change feeds and MCP. Access must preserve evidence/analysis distinctions,
version references, corrections, privacy and source-specific reuse conditions across formats.

MCP is a future Agent Access Layer, not ingestion or an authority shortcut. Read-only tool
candidates include `search_people`, `get_person_profile`, `get_issue`, `get_claim`,
`get_claim_evidence`, `trace_provenance`, `get_public_money`, `compare_people` and
`list_recent_changes`. None is an implemented MCP tool. Public defaults exclude `merge_person`,
`approve_identity`, `publish_claim`, `override_source` and `run_unbounded_scraper`.

Public interest and sustainability are compatible. Potential service tiers are free website
evidence access; public-interest API access for journalism, academia and civic organizations;
limited developer API/MCP quotas; commercial throughput, alerts and analytics; licensed bulk/change
feeds; and enterprise SLA, integration and monitoring. These are directions, not launched plans,
prices or license grants. Each SourcePolicy and upstream right governs actual storage, publication,
commercial use and redistribution. Neither public interest nor transformation cancels those rights.

Commercial value comes from normalization, identity resolution, provenance, temporal history,
correction tracking, derived analytics, stable APIs and continuous maintenance, rather than
exclusive control of raw public records. Paid delivery must not turn payment or popularity into
evidence quality or factual authority.

## Acquisition and implementation boundaries

The existing [source acquisition playbook](../architecture/FEEDER_SOURCE_COVERAGE.md#source-acquisition-playbook)
remains authoritative. Strong collection can use official APIs, source-specific crawlers, bounded
board collectors, structured disclosures, document extraction, information requests and manual
curation where the reviewed source contract permits that route. Each needs a bounded universe or
packet, rights, coverage/pagination, stable locator/key semantics, version/correction treatment
and QA appropriate to its maturity. A North Star example grants no permission for a currently
blocked source. Source-specific HTML work still needs a separately approved governing change
where V0 or a source gate prohibits it.

Generic crawling is excluded because it loses provenance and source semantics, not because large
volume is inherently prohibited. L3 blocks can coexist with rights-approved L1/L2 human-assisted
packets; this does not promote maturity or implement a generic importer. Official originals and
curated representations remain distinct Sources. No name-only identity, inferred missing values,
private-family Persons, parallel raw store or publication bypass follows from this direction.

V0's exclusions, including alerts, payments and unsupported dashboards, continue to apply to
current work. This milestone adds no code, schema, migration, dependency, feeder, collection run,
graph database, scoring tables, MCP server, social tables or algorithm. Future proposals must
reuse existing semantics first and demonstrate a concrete vertical slice before adding machinery.

## Anti-goals and success

Anti-goals are partisan persuasion, engagement-only rage feeds, opaque ideology scoring, rumor
aggregation, generic search-result ingestion, automatic guilt/wrongdoing classifiers, name-only
people graphs, anonymous untraceable AI summaries, community opinions overwriting evidence and
uncritical government PR mirrors.

Success is movement from headline or label through curiosity, evidence and context to independent
judgment. Changing a reader's political position is not a success metric. Candidate measures
include evidence inspected, sources opened, comparisons explored, multiple relevant bodies of
evidence considered, corrections discovered and API/MCP reuse. Evaluate whether readers can
understand scope and distinguish recorded fact from analysis, not just whether they click.
Page views and engagement inform the product but do not replace these outcomes. Measurement
definitions and baselines belong to future milestones; none are asserted as measured today.
