# Civic Intel API credential checklist

Checked against repository usage and official provider pages on 2026-09-24.

Never commit real keys to Git, request JSON, HANDOFF, screenshots, logs, or chat. This file records
only environment-variable names and acquisition routes. Inject credentials only into the private
collector runtime that needs them.

## Acquisition order

| Priority | Environment variable | Provider / API | Why Civic Intel needs it | Current state |
| --- | --- | --- | --- | --- |
| P0 | `NEC_API_KEY` | 중앙선거관리위원회 후보자/당선인 API | Strongest next Person-expansion lane: provider candidate ID (`huboid`) + birth date + election context | Missing |
| P0 | `ASSEMBLY_API_KEY` | 국회 국회사무처 국회의원/의안 Open API | Current roster refresh, code-first Assembly identity and bill participation | Missing on operator host / staging collector boundary |
| P1 | `DART_API_KEY` | 금융감독원 OpenDART | Corporate executive-status and related senior-person disclosure lanes | Missing |
| P1 | `MOIS_ORG_CODE_API_KEY` | 행정안전부 행정표준코드 기관코드 | Organization universe/codes; useful for organization binding, not Person identity | Missing |
| P2 | `NKIS_API_KEY` | 국가정책연구포털 NKIS Open API | Research-output/researcher discovery; does not prove employment | Missing |

ALIO item-4 and org.go current connectors do not require one of these API keys and have already
been collected through their existing permitted routes.

## P0 — NEC

Repository variable: `NEC_API_KEY`

Apply for both services used by the same connector family:
1. 후보자 정보: https://www.data.go.kr/data/15000908/openapi.do
2. 당선인 정보: https://www.data.go.kr/data/15000864/openapi.do

The current official pages describe free use, unrestricted use scope, development automatic
approval / operational review, and a development quota of 10,000 calls. The candidate API exposes
`huboid`, name and birth date; Civic Intel discards address before persistence.

On data.go.kr, log in, open each service, choose **활용신청**, and select the intended personal or
project service key. Access approval is service-specific even when the same account/project key is
selected. Store the resulting credential in the collector environment as `NEC_API_KEY`.

Do not put `ServiceKey` into stored source URLs; the connector injects it only into the outbound
request.

## P0 — National Assembly

Repository variable: `ASSEMBLY_API_KEY`

Official catalog:
https://www.data.go.kr/data/15126133/openapi.do

This is the National Assembly Secretariat integrated member-information API. The repository also
uses the same private key for reviewed Assembly bill/schedule connectors. Apply through the official
catalog/linked Open Assembly service and retain the issued key privately. The data.go.kr catalog
currently states free use, unrestricted use scope and development automatic approval / operational
review.

The connector sends the credential as the provider `KEY` parameter but deliberately keeps it out
of discovered/stored URLs and metadata.

## P1 — OpenDART

Repository variable: `DART_API_KEY`

Official key application:
https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do

OpenDART requires its own authentication key; this is not a data.go.kr service key. The official
application asks for the use environment/purpose and issues the API key after account/application
approval. OpenDART API guides describe `crtfc_key` as the required 40-character key.

Civic Intel uses this only for allowed senior/corporate disclosure lanes. Ordinary employee-status
rows are not a Person-discovery source.

## P1 — MOIS organization code

Repository variable: `MOIS_ORG_CODE_API_KEY`

Official API:
https://www.data.go.kr/data/15077870/openapi.do

Apply with **활용신청** on data.go.kr. The current page lists the endpoint
`StanOrgCd2/getStanOrgCdList2`, requires `ServiceKey`, and states development/operational
automatic approval with a development quota of 10,000 calls.

This credential expands/validates Organization codes. It must never be treated as a Person
identifier.

## P2 — NKIS

Repository variable: `NKIS_API_KEY`

Official Open API introduction/application route:
https://nkis.re.kr/openDesc.do

NKIS states that users must sign up/login, submit an Open API utilization application, wait for
administrator review, then retrieve the issued key from the authentication-key issuance history
(or email). Current contact shown by NKIS: digital communications office, 044-211-1251,
sanhak21@nrc.re.kr.

This source supports research-output/researcher discovery. An NKIS publishing institution is not
automatically the researcher's employer, and researcher labels still require identity resolution.

## After you receive the keys

Do not paste them into a tracked `.env` file. The preferred handoff is:

1. Tell MAIN only **which keys have been issued**, not their values.
2. Put values into the authorized private collector environment / secret store.
3. MAIN verifies presence by boolean/length only.
4. Run a one-request source-contract smoke test with credentials redacted from logs.
5. Run the source-specific dry-run/enumeration and inspect its receipt.
6. Only then enable the corresponding bounded staging collection.
7. Never add these keys to the public API/Web service unless that service is explicitly the private
   acquisition boundary.

Expected variable names:

```text
ASSEMBLY_API_KEY=
NEC_API_KEY=
NKIS_API_KEY=
DART_API_KEY=
MOIS_ORG_CODE_API_KEY=
```

## Current blocker relationship

The missing keys block new live acquisition from NEC, OpenDART, NKIS and MOIS, and fresh Assembly
collection. They do **not** block the current ALIO safe-person materialization slice because that
slice reads already persisted, checkpoint-verified ALIO observations and performs no source fetch.
