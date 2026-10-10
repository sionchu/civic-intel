# Official real-estate market sources — MOLIT L1 and R-ONE local L2

**Status (2026-10-10): MOLIT L1 CONTRACT_STAGED; R-ONE one-national-month L2 LOCAL_VERIFIED only.** The private R-ONE capture exists only in a disposable, Alembic-migrated SQLite proof. No production source policy, operational data, public transaction statistic, automatic map overlay, Person Claim or L3 coverage is claimed. These lanes never establish ownership of a public official's property.

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

## Official public-map statistics — separate R-ONE L1 candidate

The official MOLIT contract-date transaction pages are **not** themselves the
statistics that the MOLIT public-real-estate-site recommends for external
publication. Its [conditions-based CSV page](https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=)
states that outside publication should use the reporting-date
official statistics and warns that contract-date data can change with
late reports or cancellations. A public map must preserve that basis,
instead of relabeling a contract-date API page count as an official
reported-date statistic.

R-ONE / 한국부동산원
[Open API](https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do),
[portal dataset 15134761](https://www.data.go.kr/data/15134761/openapi.do)
is an officially documented candidate, distinct from the two MOLIT APIs.
A single bounded **no-key sample** (2026-10-10) for table
`A_2024_00546` (housing transactions including multiple types, **not**
apartment-only) returned official JSON envelope
`SttsApiTblData: [{head:[{list_total_count}, {RESULT}]}, {row:[...]}]`.
The provider advertised 137,976 rows but supplied only **five sample rows**
when no key was present. The five sample observations were for **2006-01**.
This does not establish 2026 freshness, full enumeration, nationwide
coverage, monthly series completeness or right to expose the sample as
current official statistics.

`packages/connectors/reb_market_statistics.py` implements an **offline
supplied-response parser only** for that exact housing volume table/item
(`ITM_ID=100001`, `UI_NM=동(호)수`, `DTACYCLE_CD=MM`).
It validates the official response family, result code, period, amount,
region namespace and duplicate region-month key, while discarding all
non-allowlisted fields. The result is permanently
`UNVERIFIED_PROVIDER_SAMPLE_OR_SINGLE_PAGE` and `publishable=False`.
Neither keyless sampling nor a numerical `list_total_count` is a
publication or completeness proof.

**Critical namespace separation:** R-ONE `CLS_ID` (e.g. 전국 `500001`)
is not MOLIT `LAWD_CD` (`11110` for 종로구). Any map aggregation or
joining requires an independently reviewed official region crosswalk
with version/time basis. Do not infer crosswalks or replicate old aliases
from similar names, and never join Person disclosure rows to trades.

The R-ONE [developer guide](https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do)
requires a login-issued API key for full access, supports `pIndex`/`pSize`
and says that direct browser CORS queries are unsupported. The previous
L1 parser had **no live fetch or stored policy**. The later local L2 proof
below adds a separate, explicitly bounded request and canonical storage
path, but never adds a public map statistic or operation sync.
An approved, observed full-reporting-date extract plus a source-specific
publishability decision and verified regional codes are required for a map.

## R-ONE nationwide single-month — L2 LOCAL_VERIFIED (2026-10-10)

- **Official source:** [R-ONE statistical data API](https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do),
  table `A_2024_00546`, `ITM_ID=100001`, `DTACYCLE_CD=MM`.
  Exact one-record query `CLS_ID=500001` (전국), `START_WRTTIME=202501`,
  `END_WRTTIME=202501`, `pIndex=1`, `pSize=1`.
- **Observed official result:** January 2025, **64,215 동(호)** reported total
  housing-unit transactions. Response HTTP 200 / `INFO-000`, provider total
  `1` and exactly one returned row. This is *all housing types*, not
  apartment-only trading, a sale price, an ownership record, or a current month.
- **SourcePolicy:** `packages/connectors/reb_market_statistics.py`
  `reb_housing_l2_policy()` pins the full reviewed local-use decision for the
  single source table/item/region/month. `FETCH` and `STORE_METADATA` only;
  no raw fulltext, AI, excerpt, commercial reuse or public release. The exact
  matching policy was registered **only** in a freshly Alembic-migrated
  disposable database. Existing operational policy records were not altered.
- **Canonical capture:** `workers/reb_housing_import.py` validates an
  exact one-row query and builds the existing `Source → SourceSnapshot →
  FeederObservation` trail through `SqlAlchemyRepository.commit_source_page`
  with `require_stored_policy_match=True`. The Source URL contains **no KEY
  or parameters**; snapshots and observations contain only safe numeric and
  source-scope metadata. No original response JSON, raw XML, Person link,
  Claim, public display or second source-truth store was created.
- **Local receipt:** in the owner-authorized Mac mini
  `/Users/lee/Developer/cvic-reb-l2-proof-final-20261010/reb_official_one_month.sqlite`,
  one policy, one Source, one snapshot, one FeederObservation, two success
  runs and one checkpoint. First run 1 new observation, same-input replay
  **0 new / 1 unchanged**, same snapshot. No people or Claims created.
  `SourceSnapshot.content_hash`:
  `548f71eeb4880e76cdbee732be67074f3ab1368c9291ec5ee3f4a5dd039f35d4`.
  The local DB was also checked not to contain the API key. The one-page
  source reader uses a per-call standard-library HTTPS handler with debugging
  disabled and redirects blocked; it reads at most 120KB plus one byte and
  emits fixed sanitized failure messages. No HTTPX URL INFO logging or raw
  HTTP request/response record is written into the evidence store.
- **Maturity limit:** each authorized collector invocation issues only one
  exact region/month HTTPS request; the persisted proof retains one such
  official record. This does **not** prove the provider
  universe, 2026/current-year completeness, revision history, national/region
  crosswalk, fresh scheduled synchronization, full acquisition rights for
  a public Site, or hosted/public display. `RebHousingResearchPage.publishable`
  remains `False`.

Operational prerequisites remain a reviewed publication/access decision,
a broader source-specific canonical policy, idempotent multi-month coverage,
official regional code crosswalk and current-boundary validation.

## Region outline UI preview (2026-10-10)

The standalone `/market` route now provides **boundary navigation only** using
17 historic 2020 province shapes from StatGarten/maps (MIT, based on SGIS).
The original 2020 province IDs are retained as labels and are explicitly
**not** a versioned R-ONE `CLS_ID` nor MOLIT `LAWD_CD` crosswalk. These shapes
must never authorize joins or a claim about a public official's property.
The 2020 boundaries can differ from today's administrative regions.

The screen has an accessible, keyboard-selectable province list, a separate
housing/land source selector and links to official datasets. Since there is
still **zero source-approved eligible region/month series**, it displays
`공식 거래 수치 미게시`, not zeros, synthetic prices, filled choropleths,
privacy-risky parcel pins, fake map tiles or a confidence score. Browser smoke
and authoritative public-series evidence remain separate gates. Its frontend
readiness is not source maturity or live transaction coverage.

## Relation to CVIC official asset disclosures

The existing `NATIONAL_ASSEMBLY_ASSET_DISCLOSURE.md` and PETI source contract govern **reported declared totals** and reviewed SELF-housing metadata. Their actual published operational records remain separately unverified; prior 2026-10-09 operations documented 0 new published asset/housing claims. Current resolved-person identity review never makes market transactions into that person's purchases, sales, residences, taxable wealth or unexplained assets.

Supported future UI grammar, inspired only by [Real Signal](https://real-signal.org/#/map?x=127.594722&y=36.851715&z=8):

- Separate public `지역 실거래 동향` surface with a district/month selector and official province/district geometry when licensed and separately verified; show number of active/cancelled trades, median amount, data timestamp, source and missing/partial status.
- National Assembly / official profile pages may **link to** this independent market context but must not overlay precise location pins for a person, join disclosed parcels by fuzzy address, or say `이 사람이 거래했다` without a primary registry/explicit authorized reviewed evidence.
- Aggregate market counts are **not** Claim/Evidence about a person. If operational materialization is later approved, use the canonical SourcePolicy, Source, SourceSnapshot, FeederObservation path and separate reviewed public read models; do not invent a parallel asset/ownership store or promote from raw trades to FACT.

## Next milestones / verification gates

The R-ONE **single nationwide January 2025 local L2 proof** above is complete, not the
same thing as MOLIT's still L1 apartment/land market lane or a current regional series.

1. **MOLIT L1:** deterministic offline XML/mock HTTP tests, fail-closed privacy/pagination/aggregation. Only source-specific code and this canonical source document.
2. **L2 one region/month:** owner-reviewed effective SourcePolicy and authorized API key, one official page plus sanitized SourceSnapshot/FeederObservation/SourceRun in an isolated database, exact rerun/checkpoint evidence. No raw parcel/unit, no Person linkage and no public deployment.
3. **L3:** source-defined and rights-approved region/month universe, bounded batch coordinator, stable source-page coverage, idempotent snapshots, source cancellation/revision tracking. Prove full-year coverage, not merely one district/month.
4. **Read-only map:** only after eligible regional market data is explicitly approved and the map geometry is licensed with source/time/region keys; no invented coordinates or ownership.
5. **Official assets:** PETI/Gazette reviewed disclosure total → existing reviewed Person link → separate Claim/Evidence/publication gates. Extension to other high-ranking public officers needs a separate official identity scope; a National Assembly-only packet cannot silently expand.

Privacy, accurate semantics and evidence-first public display are release gates, not model suggestions.
