# MOLIT apartment and land sales — regional market context L1

**Status (2026-10-10): L1 CONTRACT_STAGED / OFFLINE FIXTURES ONLY.** No production data collection, canonical persistence, source-policy application, Person linkage, public transaction display, map layer, or L3 coverage is claimed. This is a scoped source-adapter implementation, not public-official asset ownership evidence.

## Official sources and rights

| Lane | Provider official catalog | Source response |
|---|---|---|
| Apartment sales | [MOLIT 아파트 매매 실거래가](https://www.data.go.kr/data/15126469/openapi.do) | XML, district `LAWD_CD` (5 digits) and contract month `DEAL_YMD` (YYYYMM) |
| Land sales | [MOLIT 토지 매매 실거래가](https://www.data.go.kr/data/15126466/openapi.do) | XML, same bounded selectors |

Both official catalog pages were reviewed on 2026-10-10. They show free service, automatic approval at development/operation stage, and *이용허락범위 제한 없음*. Account-specific service authorization, provider quotas and correction/cancellation semantics are still separate gates. These APIs publish transactions in a district/month, **not the buyer/seller's validated identity or ownership register**. Apartments disclose floors and some building-level detail; land parcel numbers are partly suppressed for privacy. Their raw XML must not become public-official property evidence.

The existing host SourcePolicy at `apis.data.go.kr` is currently explicitly limited to NEC/MOIS datasets. Do not treat its `can_fetch=True` as authorization for these new two datasets. This L1 **offline** parser takes a supplied metadata-only SourcePolicy carrying the test/review scope marker `MOLIT_APPROVED_DATASETS_15126469_15126466` and the existing host policy ID; this is a fixture constraint, **not proof that a reviewed effective policy has been registered**. This release provides **no HTTP fetch or credential handling implementation**. Before any L2 request, a separately approved canonical same-host policy decision, actual dataset authorization and an account key are required; never embed credentials in Source/Snapshot/Observation/URL/log/error/fixture.

## Executable boundary

`packages/connectors/molit_transactions.py` is a source-specific **pure XML parser and summary**. The caller supplies a policy fixture and page bytes; the code never calls the provider, reads an API key or writes to any DB. It accepts one five-digit `LAWD_CD`, one calendar `DEAL_YMD`, and an exact page size (1–1000). Response header success, matching pages and totals, and full page cardinality are mandatory to return a window summary. Missing, duplicate or drifted pages fail closed. No provider-side stable transaction ID or correction history has been verified, so equal rows are **not** deduplicated or interpreted as identical transactions. The label `QUERY_PAGE_COUNTS_RECONCILED_NOT_DEDUPLICATED` explicitly states that only the supplied query's page counts were checked, not the source's historical completeness.

Only date (for scope validation), trade amount (unit: **만원**), area (for validation), and explicit cancellation code are interpreted. After checking area, the normalized in-memory page retains only the numeric amount and cancellation flag. It drops raw XML, street/parcel numbers, unit/floor, complex name, personal/buyer/seller attributes, real-estate-agent contact fields, and any exact coordinates. The public metadata return value contains only source catalog URL, region 5-digit code, month, source kind, reported/active/cancelled counts and median *active* amount. No Person UUID, household, property, address or canonical asset key exists here.

Reported transactions and cancelled transactions are distinguished. Missing or malformed date/price/area, inconsistent pagination, unrecognized cancellation codes and provider errors **fail closed**. `median_active_price_10k_krw=null` on an empty/fully cancelled input means no active transaction was observed in the **supplied query pages** — not no assets, no market activity elsewhere, a completed ownership disclosure, or zero wealth. The summary also marks `PROVIDER_CORRECTION_HISTORY_UNKNOWN`; provider revision/tombstone semantics and full-year universe are unverified.

## Relation to CVIC official asset disclosures

The existing `NATIONAL_ASSEMBLY_ASSET_DISCLOSURE.md` and PETI source contract govern **reported declared totals** and reviewed SELF-housing metadata. Their actual published operational records remain separately unverified; prior 2026-10-09 operations documented 0 new published asset/housing claims. Current resolved-person identity review never makes market transactions into that person's purchases, sales, residences, taxable wealth or unexplained assets.

Supported future UI grammar, inspired only by [Real Signal](https://real-signal.org/#/map?x=127.594722&y=36.851715&z=8):

- Separate public `지역 실거래 동향` surface with a district/month selector and official province/district geometry when licensed and separately verified; show number of active/cancelled trades, median amount, data timestamp, source and missing/partial status.
- National Assembly / official profile pages may **link to** this independent market context but must not overlay precise location pins for a person, join disclosed parcels by fuzzy address, or say `이 사람이 거래했다` without a primary registry/explicit authorized reviewed evidence.
- Aggregate market counts are **not** Claim/Evidence about a person. If operational materialization is later approved, use the canonical SourcePolicy, Source, SourceSnapshot, FeederObservation path and separate reviewed public read models; do not invent a parallel asset/ownership store or promote from raw trades to FACT.

## Next milestones / verification gates

1. **L1:** deterministic offline XML/mock HTTP tests, fail-closed privacy/pagination/aggregation. Only source-specific code and this canonical source document.
2. **L2 one region/month:** owner-reviewed effective SourcePolicy and authorized API key, one official page plus sanitized SourceSnapshot/FeederObservation/SourceRun in an isolated database, exact rerun/checkpoint evidence. No raw parcel/unit, no Person linkage and no public deployment.
3. **L3:** source-defined and rights-approved region/month universe, bounded batch coordinator, stable source-page coverage, idempotent snapshots, source cancellation/revision tracking. Prove full-year coverage, not merely one district/month.
4. **Read-only map:** only after eligible regional market data is explicitly approved and the map geometry is licensed with source/time/region keys; no invented coordinates or ownership.
5. **Official assets:** PETI/Gazette reviewed disclosure total → existing reviewed Person link → separate Claim/Evidence/publication gates. Extension to other high-ranking public officers needs a separate official identity scope; a National Assembly-only packet cannot silently expand.

Privacy, accurate semantics and evidence-first public display are release gates, not model suggestions.
