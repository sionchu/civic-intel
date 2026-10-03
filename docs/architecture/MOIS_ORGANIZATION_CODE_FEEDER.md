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

The canonical `observe mois-organization-lookup` path captures exactly the first filtered
page (1–100 rows, one connector fetch, existing 15-second HTTP operation timeout, no retry,
resume or pagination loop). It requires exactly one filter and an explicit expected full name.
The name filter must equal that expected name; a code filter must return only that code.
Provider page/size/total and first-page row count must agree before any Source data commits.
The HTTP timeout is not an end-to-end process deadline; a live runner must also enforce its
own hard process budget and exact target DB. No recurring execution is added.

The lookup uses a distinct `lookup:current:stop_selt=0:<filter>_sha256:<digest>` scope and
metadata-only SourceSnapshot. Normalized observations reuse the existing field allowlist,
retain `lookup_source_snapshot_hash` in their version hash, and carry empty identity hints.
Source/Snapshot/observations and the exact first-page manifest commit through the existing
SourceLifecycle/UoW. Identical normalized snapshot content is a no-op observation rerun;
a changed snapshot hash preserves a new immutable provenance version even if the permitted
row fields match. This is the canonical normalized SourceSnapshot hash, not an HTTP-byte hash.
The existing unfiltered L3 enumerator, scope, resume and coverage rules are unchanged.

The aggregate result reports captured count, provider filtered-query total, exact full-name
matches **within the capture**, and whether that single page covers the reported filtered
query. `SUCCESS` means the bounded page capture succeeded; it is not national/L3 coverage.
Zero captured exact names is not institution nonexistence, and one match in a truncated page
is not unique identity. Neither code equality across source namespaces nor an exact name
grants canonical Organization materialization, witness affiliation or Person identity.
The command result contains no provider rows/codes/names; it does not transmit payloads to AI.

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

The earlier org.go top-level source is a separate source family. Its reviewed 27-Organization
materialization reduced the Gukgam unresolved universe to `239` NO_EXACT mentions across `229`
distinct labels.

The complete persistent MOIS current-universe observations were then compared read-only against
only those remaining Gukgam NO_EXACT labels using exact `full_name` equality. The review-only
projection found:

- `70` distinct exact-one MOIS `full_name` proposals;
- `74` Gukgam occurrences covered by those proposals;
- `0` multiple-exact MOIS name cases in this candidate set;
- `165` mentions / `159` distinct labels still unmatched by exact MOIS `full_name`.

The canonical review artifact is
`docs/research/gukgam_2026_mois_organization_proposal_2026-09-28.json` with semantic SHA-256
`e7a208d1236517dd10d0768d1af8e25f5fc088925733b7039cbac794d9d99964`.

These matches are planning/review evidence only. The permitted sequence remains:

```text
MOIS source observation
  -> separately reviewed canonical Organization proposal
  -> existing exact-name Gukgam binding review
  -> explicit reviewed Claim manifest
```

The connector and proposal projection must not consume Gukgam text as Organization-creation
authority. Gukgam NO_EXACT rows stay unpublished until a separately reviewed Organization exists
and the existing binding review returns exactly one canonical-name match.

## Maturity

Current maturity is `L3 PERSISTENT_CURRENT_UNIVERSE_VERIFIED`:

- official current-universe API and fields are documented;
- unrestricted reuse and automatic development/operation approval are documented;
- shared host-level `apis.data.go.kr` SourcePolicy semantics are explicit;
- provider Organization keys and lifecycle fields are documented;
- credentialed 2026-09-26 live audit verified `133,907` unique current rows over `134` pages at
  `1000` rows/page and no duplicate `org_cd`;
- the merged-master persistent run on 2026-09-28 observed the then-current provider total
  `133,930`, committed `133,930` observations, advanced checkpoint `134/134`, and finished
  `SUCCESS` without canonical Person/Organization/Claim creation;
- code/date drift is covered, including uppercase-alphanumeric provider keys and three legacy/anomalous
  `crt_de` values preserved as raw text without inventing dates;
- the L3 worker persists only Source/Snapshot/FeederObservation/Checkpoint data with a bounded
  manifest digest and resume contract;
- no canonical Organization materializer or Gukgam auto-binding is authorized;
- the first post-L3 MOIS→Gukgam projection is review-only and produces `70` Organization
  proposals / `74` occurrence references with no writes.

A separate reviewed Organization materialization contract is still required before any of the
MOIS proposals may become canonical Organizations.

## Gukgam pilot lookup evidence, 2026-10-03

Two separate one-request proofs used the verified `d560efb` wheel and new disposable local
schema0008 databases. The first captured 100 of a reported 3670 filtered rows with no exact
pilot institution name in that page. The second narrowed a historical org.go discovery code
through the MOIS code filter and captured 1 of 1 with an exact pilot institution name. Source
namespace equivalence is not asserted. No provider payload was sent to AI, no fulltext was
stored and no canonical identity or Claim was created. Read-only chain/hash/manifest and
credential-exclusion audits passed; neither proof opened the operational Mac database.
These live proofs precede the new canonical worker and do not prove that worker is installed
or has run on Mac. See [the lookup receipt](../receipts/gukgam-mois-lookup-20261003.json).
