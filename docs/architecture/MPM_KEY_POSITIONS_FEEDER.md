# MPM National Key Positions Feeder

## Purpose

This feeder captures the Ministry of Personnel Management (MPM) `국가주요직위명부` as an
immutable, observation-only central-government position snapshot.

It does **not** create canonical People. The release is broad enough to include 과장급 positions,
so acquisition and identity/publication are deliberately separated.

## Reviewed source — 2026 H1

Public-data catalog:

- https://www.data.go.kr/data/15060548/fileData.do

Provider post:

- https://www.mpm.go.kr/mpm/info/hrInfo/hrInfoBoard/?boardId=bbs_0000000000000130&mode=view&cntId=44&category=&pageIdx=

The provider post was published 2026-06-29 and states that the data is as of **2026-04-30**.

The reviewed release consists of exactly three provider attachments:

| Group | File ID | Workbook |
|---|---|---|
| ministries | `FILE_000000100069052` | `2026년 상반기 국가주요직위명부(부).xlsx` |
| other | `FILE_000000100069053` | `2026년 상반기 국가주요직위명부(처,원.실.위원회.기타).xlsx` |
| agencies | `FILE_000000100069054` | `2026년 상반기 국가주요직위명부(청).xlsx` |

A read-only source audit on 2026-10-04 found:

- ministries: 17 worksheets / 3,441 position rows;
- agencies: 18 worksheets / 3,050 position rows;
- other central bodies: 17 worksheets / 1,250 position rows;
- total: **7,741 position rows**;
- explicit `공석`: **535 rows**.

The combined `국무조정실.국무총리비서실` worksheet explains why 52 worksheets can cover the
catalog's 53-institution universe.

## Workbook contract

Every reviewed worksheet has the same A:H structure after its title/as-of rows:

1. 연번
2. 소속부서 level 1
3. 소속부서 level 2
4. 직위
5. 성명
6. 직급·직무등급
7. 담당업무
8. 전화번호

The connector reads only columns A:H and requires the declared header shape. It ignores workbook
formatting cells outside H.

### Privacy minimization

Column H is never emitted by the connector.

Office phone is discarded **before** normalized JSON, content hashing, SourceSnapshot metadata,
FeederObservation creation, logs, and test assertions. The raw XLSX is used transiently in memory
and is not persisted by Civic Intel.

`공석` remains a vacancy observation with `person_name = null`. It never creates a person hint.

## Provider-record identity

The provider publishes no person ID and no row ID.

For this exact immutable release, Civic Intel uses the source locator:

`<attachment-file-id>:<worksheet-index>:<worksheet-row>`

as `provider_record_key`.

This is a **release-local observation key**, not a Person identifier. Future half-year releases use
different attachment IDs and scopes and must not be identity-merged from this key.

## SourcePolicy

The acquisition domain is `www.mpm.go.kr` because that host serves the reviewed files.

The dataset-specific license is taken from data.go.kr dataset 15060548:

- free;
- `이용허락범위 제한 없음`.

The provider robots file was checked on 2026-10-04. It disallows `/search/`, `/flexer/`, and
`/board/board.do`; the reviewed provider post and fixed `/board/file/...` delivery paths are not
listed as disallowed.

The policy therefore permits fetching and metadata storage for **this dataset only**. It does not
authorize unrelated MPM pages/files. Fulltext storage, excerpt publication, and AI transmission
remain disabled.

## L3 boundary

Feeder:

`mpm_national_key_positions`

Scope:

`as_of:2026-04-30`

Source contract:

`mpm_national_key_positions_2026_h1_v1`

A complete run fetches all three reviewed attachments and stores every parsed position row as a
FeederObservation.

Checkpoints keep only:

- completed attachment cursor;
- expected group list;
- raw SHA-256 for completed attachments;
- per-group row counts;
- total committed record count.

Resume re-fetches already completed attachments and verifies their raw hashes before continuing.
If a completed provider file changed between attempts, resume fails closed rather than mixing two
release versions.

## Identity and publication boundary

`identity_hints = {}` for every observation in this slice.

No automatic:

- Person creation;
- PersonAlias creation;
- CareerEpisode creation;
- Claim/ClaimEvidence creation;
- Organization binding;
- Gukgam binding;
- talent-pool inclusion.

A later review layer may select only positions that satisfy the civil-service public-interest scope
and must resolve identity using independent anchors. Name + agency + title is evidence context, not
automatic same-person authority.

## Gwanbo relationship

The MPM roster and the Gwanbo personnel feeder answer different questions:

- Gwanbo: dated personnel-notice publication events;
- MPM key-position roster: who the provider reported as occupying a key position at one snapshot.

They may corroborate each other, but announcement date, effective date, and roster observation date
must remain separate semantics.

The data.go.kr `행정안전부_관보_인사` REST API was also reviewed on 2026-10-04, but its Swagger
does not document the required `reqFrom` / `reqTo` string format. Civic Intel must not guess that
request contract. The existing Gwanbo acquisition path remains canonical until a credentialed or
officially documented request-format proof closes that gap.
