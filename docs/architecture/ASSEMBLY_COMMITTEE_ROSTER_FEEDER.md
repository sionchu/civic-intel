# National Assembly Committee Roster Feeder

## Purpose

Stage official National Assembly committee composition and member-role data without importing
contact information or treating an undated provider row as a historical membership episode.

This source is useful for committee-code/name context, chair and secretary text, exact
committee/member relationships keyed by official Assembly codes, and committee role/party/district
context. It is not authority for staff discovery, contact storage, a historical term, or membership
start/end dates.

## Official APIs — reviewed 2026-10-05

### Committee status

Service detail:
https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/O2Q4ZT001004PV11014

Endpoint:
https://open.assembly.go.kr/portal/openapi/nxrvzonlafugpqjuh

Documented fields:

- CMT_DIV_CD — 위원회구분코드
- CMT_DIV_NM — 위원회구분
- HR_DEPT_CD — 위원회코드
- COMMITTEE_NAME — 위원회
- HG_NM — 위원장
- HG_NM_LIST — 간사
- LIMIT_CNT — 위원정수
- CURR_CNT — 현원
- POLY99_CNT — 비교섭단체위원수
- POLY_CNT — 교섭단체위원수

### Committee member list

Service detail:
https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OCAJQ4001000LI18751

Public-data catalog:
https://www.data.go.kr/data/15126035/openapi.do

Endpoint:
https://open.assembly.go.kr/portal/openapi/nktulghcadyhmiqxi

Documented fields:

- DEPT_CD — 위원회코드
- DEPT_NM — 위원회명
- JOB_RES_NM — 구성
- HG_NM — 위원명
- ORIG_NM — 선거구
- POLY_NM — 정당
- ASSEM_TEL — 전화번호
- ASSEM_EMAIL — 이메일
- HJ_NM — 위원명(한자)
- ROOM_NO — 호실
- STAFF — 보좌관
- SECRETARY — 비서관
- SECRETARY2 — 비서
- MONA_CD — 국회의원코드

Civic Intel retains only DEPT_CD, DEPT_NM, JOB_RES_NM, HG_NM, ORIG_NM, POLY_NM, HJ_NM,
and MONA_CD. Contact, room and staff fields are discarded before the connector creates its
normalized ConnectorDocument body.

## Request contract

Both APIs use the standard Open Assembly basic arguments KEY, Type, pIndex and pSize.
The provider service pages show a request limit of 200000.

All service-specific search fields are optional. The connector only allows documented search fields
and never embeds credentials in a discovered URL.

The official developer guide states that a request without a KEY uses a bounded sample mode.
Civic Intel exposes that only as an explicit L2 verification mode fixed to page 1, size 5.
Normal mode requires ASSEMBLY_API_KEY.

## L2 live proof — 2026-10-05

The new Civic Intel connectors performed public, no-key official sample pulls:

- status: 5 rows, first committee key 9700005;
- membership: 5 rows, first relationship key 9700005:HE08888N;
- contact/staff fields in staged output: 0.

The provider raw sample headers reported status list_total_count 359, member-list list_total_count
477, and INFO-000 for both result codes. These totals are provider metadata only and are not
Civic Intel L3 coverage.

## Current-scope caution

Neither API publishes an Assembly-term field, an effective date, a membership start date, or a
membership end date.

The status API provider total (359 in the 2026-10-05 sample) is far larger than the set of currently
active standing/special committees. Therefore it is unsafe to equate its unfiltered universe with
the current 22nd Assembly committee universe.

For a future current-roster L3:

1. fully enumerate the committee-member service with an issued key;
2. require every retained MONA_CD to reconcile to the existing current-member L3 roster, or stop
   for explicit review;
3. derive the current committee-code set only from those reconciled membership rows;
4. use status records only for those member-backed committee codes;
5. preserve collection time as observation time, not an invented membership start date.

Do not infer historical membership from absence or from a later snapshot without an explicit
change/reconciliation design.

## Source identity

Committee-status provider key: exact HR_DEPT_CD.

Committee-membership provider-derived relationship key: DEPT_CD:MONA_CD.

JOB_RES_NM is relationship content. If a member changes from 위원 to 간사, a future immutable
observation should keep the same committee/member key and create a changed-content version.

These provider codes are not Civic Intel UUIDs.

## Identity / publication boundary

This L2 staging slice creates no Person, Organization/InstitutionalBody,
CommitteeMembershipEpisode, Claim/ClaimEvidence, identity link, or Gukgam committee binding.

MONA_CD is an authoritative Assembly member namespace and may be used as an exact anchor only in a
separately reviewed materialization/reconciliation step. Committee-name equality alone must not
create or bind a canonical Organization.

## Rights and attribution

Normal Open Assembly use requires an issued API key. The Open API terms prohibit unauthorized
access/key transfer and require attribution to 열린국회정보.

The existing open.assembly.go.kr SourcePolicy remains the runtime domain policy for this staged
single-pull slice. Before any persistent L3 run, reconcile the stored policy review note so the
committee APIs and current attribution review are explicitly included.

## Maturity

L2 SINGLE_PULL

Evidence:

- official request/output contracts verified;
- typed source-specific connectors;
- deterministic privacy/credential tests;
- live official sample pull through the connector;
- exact provider-derived keys documented.

L3 is blocked by the missing operational API key and unresolved full-universe current-scope
reconciliation described above.

## Full member-list enumeration and committee-office Claims (code ready, not yet run)

`civic-stage-assembly-committees --enumerate-members --database-url …` persists every row of the
committee-member list as an immutable observation:

```text
feeder: assembly_committee_memberships
scope_key: assembly_committee_member_list:current
provider_record_key: {DEPT_CD}:{MONA_CD}
semantic_scope: legislative_committee_membership_role
normalized: committee_code, committee_name, member_code, role_published (JOB_RES_NM verbatim)
```

Name, Hanja, party and district are dropped as well as the contact fields. Coverage fails closed on
a changing `list_total_count`, an incomplete page, or a duplicate/conflicting `DEPT_CD:MONA_CD`.
The checkpoint stores the full provider-hash manifest.

`--publish-roles [--dry-run]` reconciles the step 2 rule above at materialization: only rows whose
`MONA_CD` has an exact current-roster Person link are used, and unmatched codes are reported, never
name-matched. Only `위원장` and `간사` rows become `ASSEMBLY_COMMITTEE_ROLE` FACT Claims (role text
verbatim; plain `위원` membership is already the roster `ASSEMBLY_COMMITTEES` Claim). The list has
no start/end date, so the Claim is valid from collection time. A later list that drops a Person's
office is reported as `stale_claim_ids`; a changed role for the same committee fails closed. Both
need a reviewed supersession, not a silent overwrite. The import shares the exact-`MONA_CD`
contract of the bill-participation lane (`AssemblyMemberClaimLane`).

Running either command against the canonical database is an operator action that needs approval.
