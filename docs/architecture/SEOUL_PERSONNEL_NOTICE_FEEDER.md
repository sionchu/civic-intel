# Seoul Personnel Notice Attachment Feeder

## Purpose

This feeder captures the complete Seoul Open Data Plaza `서울시 인사발령 정보` dataset as
official notice/attachment observations.

It is deliberately **not** a named-person career feeder yet. The structured dataset points to the
personnel-notice attachments; the named people and precise personnel actions are inside HWP
documents and require a separate parser/source-rights review.

## Reviewed source

Dataset:

- https://data.seoul.go.kr/dataList/OA-2483/S/1/datasetView.do
- data.go.kr mirror/catalog: https://www.data.go.kr/data/15125788/fileData.do

Official full JSON download endpoint:

- https://datafile.seoul.go.kr/bigfile/iot/sheet/json/download.do

Official Open API service:

- `ListNewsPosition`
- documented sample:
  `http://openAPI.seoul.go.kr:8088/(KEY)/json/ListNewsPosition/1/5`
- public sample key was verified read-only on 2026-10-05 and reported
  `list_total_count=30`.

The Sheet UI explicitly says its preview is capped at 1,000 rows and directs users to the download
for the complete dataset. The JSON download returned all 30 current rows in one response.

## Rights and access

The dataset page identifies:

- copyright owner: Seoul Metropolitan Government;
- third-party copyright holder: none;
- license: **공공누리 제1유형** (attribution; commercial use and modification allowed);
- update frequency: irregular / when data changes.

`data.seoul.go.kr/robots.txt` allows all paths. `datafile.seoul.go.kr/robots.txt` returned 404
when checked on 2026-10-05. The fixed download endpoint is exposed by the official public Sheet
download control and does not require login or an API key.

The separate Seoul press-release pages and individual HWP documents do **not** inherit this
dataset-level policy. A reviewed press release for the 2026 H2 senior transfer carried KOGL Type 4,
so attachment/fulltext work remains a separate source-policy decision.

## Download contract

The public Sheet UI submits a POST to:

`https://datafile.seoul.go.kr/bigfile/iot/sheet/json/download.do`

with the stable dataset parameters:

- `srvType=S`
- `infId=OA-2483`
- `serviceKind=1`
- `pageNo=1`
- empty `strWhere`
- `strOrderby=CREATE_DATE DESC`
- `filterCol=필터선택`
- empty `txtFilter`

The UI also carries `gridTotalCnt` and `ssUserId=SAMPLE_VIEW`, but read-only verification showed
the endpoint returns the same complete 30-row dataset when both are omitted. They are therefore not
part of the connector contract.

The download payload contains:

- `DESCRIPTION`: provider field descriptions;
- `DATA`: the complete current rows.

## Field minimization

The provider exposes:

`BOARD_ID, TITLE, KOR_NAME, CREATE_DATE, UPDATE_DATE, ORGAN, POSITION, TEL, EMAIL, CONTENTS,
READ_CNT, START_DATE, END_DATE, DATE_CHECK, FILE_COUNT, FILE_APPD_ID, APPD_FILE_NAME, FILE_SIZE,
FILE_URL`.

Civic Intel retains only:

- board ID;
- title;
- create/update dates when supplied;
- managing organization/department;
- start/end dates;
- provider new/old marker;
- attachment count/ID/name/size/URL.

It discards before normalized JSON and hashing:

- `KOR_NAME` — notice author, commonly masked and not the appointed person;
- `TEL`;
- `EMAIL`;
- `CONTENTS` — source body/fulltext;
- `READ_CNT`.

No discarded value reaches SourceSnapshot metadata, FeederObservation, checkpoint, run receipt or
error summary.

## Provider identity

Provider record key: exact `BOARD_ID`.

The current source assigns distinct BOARD_IDs to separate attachment rows belonging to the same
parent personnel post, for example the 3급, 행정4급 and 기술연구4급 files within one release.

BOARD_ID is therefore a provider **notice-attachment record** identifier, not a Person ID and not
authority to link people.

## L3 contract

Feeder:

`seoul_personnel_notice_attachments`

Scope:

`dataset:OA-2483`

Source contract:

`seoul_personnel_oa2483_json_v1`

The source is one atomic full-download universe, not a paged acquisition. A successful run:

1. fetches the complete JSON download;
2. validates DESCRIPTION/DATA shape and required source fields;
3. validates unique non-empty BOARD_ID;
4. constructs a minimized canonical JSON representation;
5. persists one Source, one SourceSnapshot and one observation per BOARD_ID;
6. commits a completion checkpoint containing record count and manifest SHA-256.

A failed fetch/parse has no committed partial page to resume; recovery restarts the single bounded
download. Unchanged reruns are idempotent. A changed normalized row under the same BOARD_ID creates
a new immutable observation version.

## Live disposable proof — 2026-10-05

A fresh SQLite database migrated through schema 0008 was used for a real, read-only provider fetch.

Result:

- SourceRun: SUCCESS
- current provider rows / observations: **30 / 30**
- checkpoint cursor: `complete`
- manifest SHA-256:
  `c860a63826af167e18f45846c1d771d4f373cdc7d569cf5974d9575405fbda1e`
- Source / SourceSnapshot: 1 / 1
- normalized forbidden keys: 0
- canonical People / Organizations / Claims: **0 / 0 / 0**

No canonical/staging database was touched.

## Next semantic boundary

The next useful layer is a separately reviewed HWP personnel-action parser that can preserve:

- exact named person;
- previous/new office;
- action type;
- effective date;
- attachment locator.

Until that source contract and rights decision exist, these observations remain discovery/evidence
pointers and must not create `CivilServiceCareerEpisode` or publish appointment FACTs.
