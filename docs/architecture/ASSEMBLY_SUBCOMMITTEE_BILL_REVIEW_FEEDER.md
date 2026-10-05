# National Assembly Subcommittee Bill Review Feeder

## Purpose

Stage official National Assembly subcommittee bill-review metadata from Open Assembly without
inventing a review-event identifier or prematurely binding the rows to canonical committees,
Bills, Claims, or Organizations.

The source records how a bill was referred to and, when available, tabled and processed in a
subcommittee. It is not a transcript and does not identify speakers or individual legislators.

## Official source — reviewed 2026-10-05

Service detail:

https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11542

API code and endpoint:

- TVBPMCONFINFO
- https://open.assembly.go.kr/portal/openapi/TVBPMCONFINFO

The official page reports version 1 dated 2026-07-07 and a request-limit value of 200000.

### Request contract

Standard Open Assembly arguments:

- KEY — required for normal use
- Type — xml/json
- pIndex — page index
- pSize — page size

Service-specific arguments:

- AGE — required Assembly term; official example 22
- BILL_NO — optional bill number
- BILL_ID — optional bill ID
- ENROLL_TYPE — optional direct-subcommittee-referral flag; official example Y

All service filters other than AGE are optional, so the API contract supports an unfiltered query
within one declared AGE. Full enumeration is not claimed until an issued key is used and every page
passes the normal L3 coverage gates.

## Output contract

The official service documents exactly 16 fields:

- AGE — 대수
- BILL_NO — 의안번호
- BILL_ID — 의안ID
- COMMITTEE_ID — 위원회ID
- COMMITTEE_NAME — 소관위명
- SUB_COMMITTEE_NAME — 소위원회명
- PRESENT_SESSION — 상정회기
- PRESENT_CHA — 상정차수
- PROC_SESSION — 의결회기
- PROC_CHA — 의결차수
- SUBMIT_DT — 회부일
- PRESENT_DT — 상정일
- PROC_DT — 처리일
- PROC_RESULT_CD — 의안심의결과
- ENROLL_TYPE — 소위직접회부여부
- CONF_BIGO — 소위회부정보

No person, contact, address, room, or staff fields are documented.

## L2 official sample proof

The official no-key sample for AGE=22 was verified twice:

1. the provider sample URL shown on the service page returned XML;
2. the Civic Intel connector requested the same sample as JSON with page 1 / size 5.

Both reported:

- result code INFO-000;
- list_total_count 18324;
- five sample rows.

The first sample row had BILL_ID
PRC_R2I4R0J5J3T0L1S0T1F7I2T5J6G9L8, COMMITTEE_ID 9700407, SUBMIT_DT 2024-08-21,
ENROLL_TYPE N, and no subcommittee/table/decision fields yet.

Other sample rows demonstrated populated subcommittee/session/date/result fields, including
PROC_RESULT_CD values such as 대안반영폐기.

## Semantic mapping

Civic Intel preserves the provider semantics directly:

- SUBMIT_DT -> referral_date
- PRESENT_DT -> present_date
- PROC_DT -> process_date
- PRESENT_SESSION / PRESENT_CHA -> table session / meeting sequence
- PROC_SESSION / PROC_CHA -> processing session / meeting sequence
- PROC_RESULT_CD -> source-reported review result text
- ENROLL_TYPE -> direct_referral boolean when Y/N
- CONF_BIGO -> source review/referral note

A missing provider value remains null. The connector rejects malformed non-empty ISO dates,
unexpected ENROLL_TYPE values, and AGE drift.

PROC_RESULT_CD is not reinterpreted as an internal Civic Intel code simply because its provider
field name ends in _CD. The sample values are human-readable result text.

## Record identity boundary

The provider documents BILL_ID as bill identity but does **not** document a stable subcommittee
review-row/event ID.

Civic Intel therefore does not assign a FeederObservation provider_record_key in this L2 slice.

Do not assume BILL_ID is unique across the full TVBPMCONFINFO universe. The official contract does
not state row-level uniqueness. A complete keyed enumeration must measure BILL_ID duplication rather
than infer it.

Before L3, analyze exact duplicate frequency for BILL_ID and candidate source-derived composites.
Only then approve an immutable observation key.

## SourcePolicy and credentials

The connector reuses the existing reviewed open.assembly.go.kr bill SourcePolicy as an L2
network-permission gate.

Normal mode requires ASSEMBLY_API_KEY. The credential is appended only to the outgoing HTTP
request and never enters discovered URLs, normalized bodies, staged output, metadata, or errors.

The official Open Assembly terms require issued-key use for normal operation and source attribution.
Before persistent L3 collection, reconcile the shared domain policy note to explicitly include
TVBPMCONFINFO and the 2026-10-05 terms/source review.

## Sample mode

The official developer guide defines a bounded sample mode when no key is supplied. Civic Intel
exposes it explicitly and fixes it to:

- page 1
- size 5
- a required AGE

Sample mode exists only for source-contract verification. Its list_total_count is provider metadata,
not evidence that Civic Intel enumerated the universe.

## Identity and publication boundary

This source creates no:

- Person or identity candidate;
- Organization / InstitutionalBody;
- CommitteeMembershipEpisode;
- canonical Bill binding;
- Claim / ClaimEvidence;
- public projection.

COMMITTEE_ID and BILL_ID are provider namespaces that can support later exact joins only after the
relevant source-specific review.

## Maturity

L2 SINGLE_PULL.

Evidence:

- current official service/request/output contract verified;
- typed connector with strict parsing;
- credential-safe official sample mode;
- deterministic regression tests;
- live official JSON sample through the new connector.

L3 remains blocked by issued-key execution, full enumeration, stable row-key proof, correction
semantics, and committee/bill join review.
