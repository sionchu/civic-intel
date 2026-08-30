# V0 scope

V0 proves a policy-first pipeline using Golden Set 001: the ten people named in the
2026-08-30 presidential personnel briefing. The fixture stores manually reviewed source
metadata, short excerpts, identity anchors, atomic claims, evidence stances, origin
clusters, relationships, and decision episodes. Golden and CI tests never access live
data sources.

After Golden Set 001 passed, V0 permits narrowly scoped, explicitly reviewed official-data
connectors. A reviewed connector may progress from one-record or one-page staging to bounded
full enumeration of its declared official source universe. Full enumeration must remain
source-specific and policy-first, with persistent run receipts, committed checkpoints,
idempotent record observations, coverage validation and deterministic offline tests. It does
not include scheduled synchronization or generic crawling.

The first reference source is the credential-gated National Assembly member-information Open
API. A connector, enumerator or worker does not gain publication authority: SourcePolicy,
identity materialization, evidence verification and publishability gates remain mandatory.
`ReviewedPersonBundle` remains the manual, regression and exceptional onboarding path; it is
not required for every safely materialized batch identity. The public-official-profiler is an
optional deep-evidence enrichment consumer after canonical identity, not the normal batch
ingestion path.

Private-family discovery, precise residence, paywall bypass, payments, alerts, broad
crawling, Neo4j, Elasticsearch, Kafka, and Kubernetes are prohibited. Raw search results
and workers cannot publish profile content.
