# MOIS Standard Organization Code Feeder

## Scope

This source contract covers the Ministry of the Interior and Safety public-data portal API
`행정안전부_행정표준코드_기관코드` (`data.go.kr` dataset `15077870`). The API exposes current
organization-code rows from the Administrative Standard Code Management System.

The current Civic Intel implementation may persist a complete current provider Organization-code
universe as immutable Source/Snapshot/FeederObservation data, but it does not create canonical
Organizations, publish Claims, or bind Gukgam audited-target text automatically.

## Official contract

Reviewed on 2026-09-22:

```text
catalog: https://www.data.go.kr/data/15077870/openapi.do
endpoint: https://apis.data.go.kr/1741000/StanOrgCd2/getStanOrgCdList2
service: https://apis.data.go.kr/1741000/StanOrgCd2
provider: 행정안전부
format: JSON or XML
license: 이용허락범위 제한 없음
approval: development automatic / operation automatic
```

Required request parameters are `ServiceKey`, `pageNo`, `numOfRows` and `type`. Civic Intel uses
`type=json` and defaults to `stop_selt=0` so contract discovery remains current-institution only.
Optional `full_nm` and `org_cd` filters are permitted for bounded review pulls.

`ServiceKey` is injected only at request time. Discovery URLs, Source URLs, metadata, normalized
records, errors and fixtures must never contain it. The source-specific runtime variable is
`MOIS_ORG_CODE_API_KEY`. A credentialed read-only live audit completed on 2026-09-26 without
persisting the credential or request secret.

## Provider identity and hierarchy

The provider Organization key is the seven-character uppercase-alphanumeric `org_cd`. A full
2026-09-26 live audit observed numeric codes, `B/C/D/P`-prefixed codes, and mixed forms such as
`1Z00189`. It is a source namespace, not a Civic Intel canonical Organization UUID and not
authority for a cross-source identity merge.

The typed source record preserves:

```text
org_cd, full_nm, low_nm, abbr_nm
gap_no, rank_no, sub_chasu
high_cd, highst_cd, rep_cd
typebig_nm, typemid_nm, typesml_nm
locatstd_cd, use_cd
crt_de, cls_de, stop_selt, chg_de, base_date, adpt_date, preorg_cd
```

`full_nm` is the provider's full hierarchical institution name; `low_nm` is the lowest-level
organization name. Civic Intel must not silently replace one with the other. `use_cd` is retained
as a provider `use_code` value without assigning a stronger lifecycle or identity meaning. A future
canonical Organization proposal must state which provider field is used as the proposed display
name and retain the exact `org_cd` plus hierarchy fields as source evidence.

## Version and lifecycle semantics

The API supplies provider lifecycle fields rather than requiring Civic Intel to infer them:

- `crt_de`: creation date;
- `chg_de`: change date;
- `base_date`: base date;
- `adpt_date`: application date;
- `cls_de`: abolition date;
- `stop_selt`: current/abolished selector;
- `preorg_cd`: previous Organization code where supplied.

A changed provider row under the same `org_cd` is a new source observation candidate. Civic Intel
does not call it a rename, reorganization, succession or correction unless the provider fields
support that interpretation. `preorg_cd` may be evidence for a future reviewed lineage relation;
it never authorizes automatic canonical Organization replacement.

## Gukgam boundary

Post-coverage audit found `280` current `NO_EXACT_CANONICAL_NAME_OVERLAP` Gukgam mentions across
`256` distinct labels. Exact-name comparison against the official current top-level institution
set found `27` distinct labels / `41` occurrences that this source could potentially cover.

Those overlaps are planning evidence only. The permitted sequence is:

```text
MOIS source observation
  -> separately reviewed canonical Organization proposal
  -> existing exact-name Gukgam binding review
  -> explicit reviewed Claim manifest
```

The connector must not consume Gukgam text as an Organization-creation input. Gukgam `NO_EXACT`
rows stay unpublished until an independently sourced Organization exists and the existing binding
review returns exactly one canonical-name match.

## Maturity

Current maturity is `L2 LIVE_CONTRACT_VERIFIED` with an L3 worker implemented and awaiting the first
persistent merged-master staging run:

- official current-universe API and fields are documented;
- unrestricted reuse and automatic development/operation approval are documented;
- shared host-level `apis.data.go.kr` SourcePolicy semantics are explicit;
- provider Organization keys and lifecycle fields are documented;
- credentialed 2026-09-26 live audit verified `133,907` unique current rows over `134` pages at
  `1000` rows/page and no duplicate `org_cd`;
- code/date drift is covered, including uppercase-alphanumeric provider keys and three legacy/anomalous
  `crt_de` values preserved as raw text without inventing dates;
- the L3 worker persists only Source/Snapshot/FeederObservation/Checkpoint data with a bounded
  manifest digest and resume contract;
- no canonical Organization materializer or Gukgam auto-binding is authorized.

L3 is reached only after one complete persistent merged-master staging run and post-verification.
A separate reviewed Organization materialization contract is still required afterward.
