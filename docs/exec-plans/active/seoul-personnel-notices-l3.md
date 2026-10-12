# Seoul Personnel Notice Attachments L3

Status: IN_PROGRESS

## Objective

Persist the complete official Seoul Open Data Plaza `서울시 인사발령 정보` dataset as
immutable notice/attachment observations without parsing HWP attachments and without creating
canonical People, Organizations, CareerEpisodes or Claims.

## Reviewed source

- dataset UI: https://data.seoul.go.kr/dataList/OA-2483/S/1/datasetView.do
- data.go.kr catalog: https://www.data.go.kr/data/15125788/fileData.do
- full JSON download endpoint:
  https://datafile.seoul.go.kr/bigfile/iot/sheet/json/download.do
- Open API service name: `ListNewsPosition`
- current full-download universe observed 2026-10-05: 30 rows
- current Open API sample `list_total_count`: 30
- update mode: irregular / on change

The dataset page declares Seoul Metropolitan Government as copyright owner, no third-party
copyright holder, and KOGL Type 1 (attribution; commercial use and modification allowed).

The public Sheet UI submits the full JSON download with a credential-free POST. The tested
minimal request fields are:

- `srvType=S`
- `infId=OA-2483`
- `serviceKind=1`
- `pageNo=1`
- `strWhere=`
- `strOrderby=CREATE_DATE DESC`
- `filterCol=필터선택`
- `txtFilter=`

`gridTotalCnt` and the UI's `ssUserId=SAMPLE_VIEW` are not required by the public download
endpoint and must not become connector state.

## Provider schema

The official dataset exposes fields including `BOARD_ID`, title, author, dates, managing
organization/department, phone, email, contents, view count and attachment metadata.

Civic Intel retains only source/attachment metadata needed for later personnel-document review:

- `board_id`
- `title`
- `create_date`
- `update_date`
- `organ`
- `position`
- `start_date`
- `end_date`
- `date_check`
- `file_count`
- `file_appd_id`
- `appd_file_name`
- `file_size`
- `file_url`

Discard before normalization/hashing/storage:

- `KOR_NAME`
- `TEL`
- `EMAIL`
- `CONTENTS`
- `READ_CNT`

## Identity and semantics

Provider record key: exact `BOARD_ID`.

The current dataset uses distinct BOARD_ID values for individual attachment rows under the same
personnel-notice post. It is a provider record identifier, not a Person identifier.

`identity_hints={}` for every observation.

The feeder represents **notice attachment discovery**, not an appointment fact. Named personnel
and exact action/effective-date semantics remain inside the attached HWP documents and require a
separate rights-reviewed parser/source gate.

## L3 mechanics

Feeder: `seoul_personnel_notice_attachments`

Scope: `dataset:OA-2483`

Source contract: `seoul_personnel_oa2483_json_v1`

The provider publishes the dataset as one full JSON download rather than a paged file universe.
The worker therefore commits one atomic Source/Snapshot/observation batch and a completion
checkpoint. Failed acquisition before commit restarts the single bounded download from the
beginning; there is no partial-page state to resume.

Required proofs:

- response shape and DESCRIPTION schema;
- unique non-empty BOARD_ID for every row;
- no phone/email/author/content/view-count persistence;
- unchanged rerun idempotency;
- changed provider row creates an immutable observation version;
- policy denial before network;
- no Person/Organization/Claim mutation;
- disposable live full-download proof;
- full repository verification.

## Stop condition

Stop after the observation-only full dataset is proven against a disposable migrated database.
Do not fetch/parse HWP attachments in this slice and do not mutate canonical staging.
