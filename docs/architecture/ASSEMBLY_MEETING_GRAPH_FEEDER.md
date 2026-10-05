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

## L3 per-age enumeration — keyed, 2026-10-05

`civic-stage-assembly-meeting-graph-age --age 22 --from-year 2024 --enumerate`
(`workers/assembly_meeting_graph_enumeration.py`).

The universe is the meeting-universe lane ([ASSEMBLY_MEETING_UNIVERSE_FEEDER.md](ASSEMBLY_MEETING_UNIVERSE_FEEDER.md)),
re-fetched and validated at the start of every run. For each `CONF_ID`, in sorted order, the run
fetches every page of `VCONFDETAIL`, `VCONFBLLLIST` and `VCONFBILLLIST` and requires:

- at least one detail row; several detail rows are accepted only when they differ in nothing but
  the meeting-type Y/N flags (observed: 4 meetings, e.g. `053887` is published once with
  `HRG_YN=Y` and once with `PBHRG_YN=Y`). The merged flag is True if any row says Y and the
  per-row flag sets are kept verbatim (`detail_row_flag_sets`); any other difference fails closed;
- detail `CONF_DT` equal to the minutes-index date;
- every agenda and bill row carrying the detail's `ERACO / SESS / DGR`;
- stable provider totals and complete pages.

One FeederObservation per `CONF_ID` (feeder `assembly_meeting_graph`, scope `assembly_age:22`):
the detail fields, `agendas` in provider order, `bills`, and the bill reconciliation below.
`agenda_to_bill_edges` is always 0.

### Provider quirks in VCONFBILLLIST (recorded, not corrected)

- Identical repeated rows: collapsed into one entry with `provider_row_count`
  (546 surplus rows across the term).
- One `BILL_ID` listed in one meeting with **different** bill names (different proposers and
  printed 의안번호 in the name): 188 instances, 152 distinct `BILL_ID`s, 51 meetings. Every
  variant row is kept, the `BILL_ID` is listed in `bill_id_conflicts`, and it is **excluded** from
  `exact_bill_ids`. The printed 의안번호 inside `BILL_NM` is not used to repair the identifier.

### Result

| measure | value |
|---|---|
| meetings (`CONF_ID`) | 1,954 — SUCCESS, complete |
| agenda rows | 49,144 (max 764 in one meeting) |
| bill rows as published | 46,345 |
| distinct bill entries | 45,799 |
| exact meeting → bill edges | 45,423 over 18,953 distinct `BILL_ID`s |
| meetings with a `BILL_ID` conflict | 51 |
| meetings with no bill rows | 429 |
| meetings with a subcommittee name | 711 |
| snapshots | 5,862 |
| Person / Organization / Claim | 0 / 0 / 0 |

Checkpoint metadata stores the universe fingerprint; `--resume` continues at the next meeting and
refuses to run if the universe changed. `--max-meetings` bounds one invocation (run ends PARTIAL).

## Maturity

**L3 FULL_ENUMERATION** for the 22nd Assembly over the meeting universe (plenary + committee
minutes indexes): every `CONF_ID` expanded, keyed, with resume and an idempotent re-run recorded
in [assembly-meeting-graph-l3-v0.md](../exec-plans/completed/assembly-meeting-graph-l3-v0.md).

Still open:

1. agenda rows are stored inside the meeting observation; no per-agenda-row provider key is
   approved (the provider documents none);
2. `BILL_ID` conflicts need a reviewed resolution path (e.g. against the bill feeder's own rows)
   before those edges can be used;
3. reviewed committee (`CMIT_NM` / `DEPT_CD`) and bill canonical joins;
4. national audit / investigation meetings are outside the universe;
5. scheduling in `civic-acquire`.
