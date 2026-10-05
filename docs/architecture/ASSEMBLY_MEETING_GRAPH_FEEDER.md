# National Assembly Meeting Graph Feeder

## Purpose

Stage a meeting-scoped legislative graph from three official Open Assembly APIs:

```text
Meeting (CONF_ID)
  ├─> Agenda rows (BLL_NO)
  └─> Bill rows (BILL_ID)
```

The graph deliberately does not create an agenda-to-bill edge. The provider exposes two different
lists with different identifiers and even different cardinalities.

## Official APIs — reviewed 2026-10-05

All three service pages report version 1 dated 2024-03-01 and request-limit value 200000.

### Meeting detail — VCONFDETAIL

Service:
https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11520

Endpoint:
https://open.assembly.go.kr/portal/openapi/VCONFDETAIL

Required service argument: `CONF_ID`.

Documented output:

- `CONF_ID` — 회의ID
- `ERACO` — 대수
- `SESS` — 회기
- `DGR` — 차수
- `CONF_DT` — 회의일자
- `CONF_KND` — 회의종류
- `CMIT_NM` — 위원회명
- `SB_CMIT_NM` — 소위원회명
- `CONF_PLC` — 회의장소
- `BG_PTM` — 시작시간
- `ED_PTM` — 종료시간
- `CONF_PTM` — 회의시간
- `HR_HRG_YN` — 인사청문회여부
- `PBHRG_YN` — 공청회여부
- `HRG_YN` — 청문회여부
- `SITG_YN` — 연석회의여부
- `RMND_SPH_YN` — 대통령위임연설여부
- `RDJM_SPH_YN` — 대통령시정연설여부
- `FRNGUS_SPH_YN` — 외빈연설여부
- `DOWN_URL` — 다운로드 URL

`CONF_ID` is the provider meeting identifier.

### Meeting agenda list — VCONFBLLLIST

Service:
https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11524

Endpoint:
https://open.assembly.go.kr/portal/openapi/VCONFBLLLIST

Required service argument: `CONF_ID`.

Documented output:

- `CONF_ID` — 회의ID
- `ERACO` — 대수
- `SESS` — 회기
- `DGR` — 차수
- `BLL_NO` — 안건 번호
- `BLL_NM` — 안건명
- `BLL_LV` — 안건 레벨

`BLL_NO` is an **agenda number**. It must not be renamed or interpreted as a bill number or
`BILL_ID`.

### Meeting bill list — VCONFBILLLIST

Service:
https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11525

Endpoint:
https://open.assembly.go.kr/portal/openapi/VCONFBILLLIST

The provider documents `CONF_ID` and `BILL_ID` as optional query arguments. Civic Intel's
meeting-graph connector deliberately requires `CONF_ID` so this source remains bounded to one
meeting.

Documented output:

- `CONF_ID` — 회의ID
- `ERACO` — 대수
- `SESS` — 회기
- `DGR` — 차수
- `BILL_ID` — 의안 ID
- `BILL_NM` — 의안명
- `LINK_URL` — 링크 URL

`BILL_ID` is the exact provider bill identifier.

## L2 aligned live proof

The implemented connectors were run in official no-key sample mode against `CONF_ID=053084`.

Observed result:

- meeting detail total: **1**
- agenda provider total: **73**
- bill provider total: **72**
- staged agenda rows: 5
- staged bill rows: 5
- result codes: INFO-000
- meeting date: 2023-07-27
- first agenda number: 1
- first bill ID: `PRC_W2L3Z0U7S2K7Y1D3G0L4L4H7O6S0A2`
- exact agenda-to-bill edges created: **0**

The 73-vs-72 provider totals are direct evidence that the two lists cannot be treated as a
positionally aligned or one-to-one dataset.

## Graph semantics

Exact edges:

1. `CONF_ID -> agenda row` because every agenda row carries the same documented meeting ID.
2. `CONF_ID -> BILL_ID` because every bill row carries both identifiers.

Not exact and therefore not created:

- `BLL_NO -> BILL_ID`
- agenda title -> bill title
- row N in agenda list -> row N in bill list
- numeric text inside an agenda name -> a canonical bill

If a later official source provides an explicit agenda-to-bill identifier, that can be added as a
separate reviewed join.

## Meeting semantics

The connector preserves:

- meeting date and provider meeting kind;
- committee/subcommittee names;
- place and provider start/end/duration strings;
- all documented hearing/joint/speech Y/N flags;
- the minutes PDF download URL.

Y/N fields are parsed strictly. Unknown non-empty values fail closed. Meeting date must be ISO
YYYY-MM-DD. Empty optional values remain null.

The download/link URLs are HTTPS-only and have credential-shaped query parameters removed before
the normalized ConnectorDocument body is created.

## Source identity boundary

Evidence-backed identifiers:

- meeting: `CONF_ID`
- bill: `BILL_ID`
- agenda number within a returned meeting: `BLL_NO`

This L2 slice does not persist observations and therefore does not approve a permanent agenda-row
provider key or meeting-bill relationship key.

For future L3, `CONF_ID:BILL_ID` is a strong candidate relationship locator because both values
are source-provided, but persistence/version semantics must still be reviewed with a complete
enumeration.

## SourcePolicy / privacy

No person/contact/staff/private fields are documented by these services.

The existing reviewed `open.assembly.go.kr` policy is reused only as the L2 fetch gate. Normal
operation requires `ASSEMBLY_API_KEY`; sample mode is explicitly page 1 / size 5 and sends no key.

Credentials never enter discovered URLs, normalized bodies, metadata, staged output or errors.

Open Assembly source-attribution requirements apply. Before persistent L3 ingestion, reconcile the
shared policy note for the three meeting endpoints and current terms review.

## Maturity

**L2 SINGLE_PULL**

Proven:

- current official request/output contracts;
- typed connectors for all three services;
- strict graph-context reconciliation across `CONF_ID / ERACO / SESS / DGR`;
- privacy/credential-safe URLs;
- live aligned sample;
- no inferred agenda-to-bill join.

L3 is blocked by:

1. issued-key execution;
2. ~~a bounded complete `CONF_ID` meeting universe~~ — acquired for the plenary and committee
   minutes indexes by [ASSEMBLY_MEETING_UNIVERSE_FEEDER.md](ASSEMBLY_MEETING_UNIVERSE_FEEDER.md)
   (22nd Assembly: 1,954 meetings); expanding each universe `CONF_ID` is still open;
3. page/checkpoint/resume/idempotency coverage;
4. agenda-row and meeting-bill relation version semantics;
5. reviewed committee and bill canonical joins.
