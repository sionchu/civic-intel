# MPM National Key Positions Source v0

Status: COMPLETE — disposable live L3 proof and repository-wide verification passed.

## Objective

Add a source-specific, rights-reviewed acquisition path for the Ministry of Personnel Management
2026 H1 국가주요직위명부 without creating or publishing canonical People.

The exact provider release is dated 2026-06-29 and describes the roster as of 2026-04-30.
It consists of three official XLSX attachments covering ministries, agencies, and
처·원·실·위원회·기타.

## Source gate

- catalog: https://www.data.go.kr/data/15060548/fileData.do
- provider post: https://www.mpm.go.kr/mpm/info/hrInfo/hrInfoBoard/?boardId=bbs_0000000000000130&mode=view&cntId=44&category=&pageIdx=
- dataset license: 이용허락범위 제한 없음
- provider robots reviewed 2026-10-04: /search/, /flexer/, /board/board.do are disallowed; the
  provider post and fixed /board/file/... delivery paths are not named as disallowed.
- public catalog fields include office phone, but Civic Intel must discard it before normalization,
  hashing, snapshots, observations, logs, or tests.

## Verified release shape

- ministries: 17 worksheets / 3,441 rows
- agencies: 18 worksheets / 3,050 rows
- other central bodies: 17 worksheets / 1,250 rows
- exact release total: 7,741 source rows
- 535 rows are explicitly 공석 and must never become a person identity hint
- schema columns A:H: sequence, department level 1, department level 2, position, name,
  grade/job level, responsibilities, office phone

## Implementation boundary

Create:

1. one MPM-specific SourcePolicy for www.mpm.go.kr;
2. a fixed-release connector that downloads only the three reviewed attachments;
3. a stdlib-only XLSX parser that reads the declared A:H contract but emits no phone field;
4. an observation-only enumerator for the exact 2026-04-30 release;
5. deterministic fixtures/tests, docs, and a disposable live proof.

Provider record key is release-local source provenance, not a Person key:
`<attachment-file-id>:<worksheet-index>:<worksheet-row>`.

No Person, PersonAlias, CareerEpisode, Claim, IdentityCandidate, or Gukgam binding is created in
this slice. A later reviewed materialization step may select only roles that satisfy the civil-service
public-interest scope.

## Verification gates

- connector unit tests cover workbook schema, phone minimization, vacant rows, malformed files,
  fixed URL validation, and source policy;
- worker tests cover three-attachment completeness, checkpoint/resume, idempotency, and no canonical
  Person/Organization/Claim mutation;
- disposable live fetch confirms the official release still parses to the verified shape;
- full `make verify` and diff review.



## Disposable live proof — 2026-10-04

A read-only live fetch of the three reviewed attachments was parsed and persisted into a fresh
SQLite database migrated through schema 0008. No canonical or staging database was touched.

Observed provider files:

- ministries SHA-256: `BE38A85BF93AFF1C94C24ED235706361E4B73C555F3F0C2EEC3750523F5C4EAD`
- other SHA-256: `990EF3FA81BDFB7AFF894E93D58F417F6985FDF91836832EB48E39E9880CA4FD`
- agencies SHA-256: `84C380E7818B731E284239D764FC49535558C2ACAF3598A377F1EC6EB2D8CE1A`

Result:

- SourceRun: SUCCESS
- attachments: 3 / 3
- FeederObservations: 7,741
- explicit vacant rows: 535
- Source rows / SourceSnapshots: 3 / 3
- normalized phone keys: 0
- canonical People / Organizations / Claims: 0 / 0 / 0

The live workbooks also exposed two verified header variations: one worksheet omits spaces in
`2)직위` / `3)성명`, and 금융위원회 labels the phone column `7) 전화번호`. The parser
accepts only these semantic header labels after whitespace normalization; it does not relax the
required column meanings.



## Verification closure

Repository-wide verification was run on Windows using the exact Makefile gates because GNU Make is
not installed on that host:

- Ruff: PASS
- mypy: PASS, 115 source files
- pytest: PASS, 783 passed / 3 skipped / 6 pre-existing SQLite datetime deprecation warnings
- Golden quality report: PASS, all checks true
- web lint: PASS
- web typecheck: PASS
- web tests: PASS, 42 / 42
- Next.js production build: PASS
- standalone runtime asset preparation: PASS

The first web-gate attempt correctly failed because the isolated worktree had no node_modules.
`npm ci` restored exactly the lockfile dependencies; no dependency or lockfile changes were made.

## Stop condition

Stop after observation-layer collection is proven on a disposable database and documentation is
updated. Do not run against canonical staging or publish any person claim.
