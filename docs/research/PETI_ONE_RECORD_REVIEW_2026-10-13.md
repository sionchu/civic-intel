# PETI 공개기록 한 건 — 사람의 확인이 필요한 항목

상태: 로컬 기본 검증 완료 / 실제 신원 확인 및 운영 반영 미실행.
이 문서는 확인 요청이며 승인이나 공개 완료 기록이 아니다.

## 확인 대상

| 항목 | 보존된 후보의 공개 메타데이터 |
|---|---|
| 표기 이름·직위 | 이준석 / 국회 / 국회의원 |
| 공개일 | 2026-03-26 |
| 등록기준일 | 2025-12-31 |
| 종전가액 | 1,470,897천원 |
| 증가액 | 105,310천원 |
| 감소액 | 252,013천원 |
| 현재가액 | 1,324,194천원 |
| 의미 | 공개된 신고 총계. 본인만의 재산·시가·순자산으로 해석하지 않음 |
| 신고 유형 | UNKNOWN — 원자료에서 확인되지 않은 유형을 보충하지 않음 |

공식 확인 입구: [공직윤리시스템 재산공개](https://www.peti.go.kr/peOptpListVie.do).
보존된 상세 경로는 `/peoptp/openPeOptpListVieDtlPop.do`이며 세션/선택자를 포함한
공유 가능한 직접 링크는 확인되지 않았다. 이름·기관·공개일·등록기준일로 정확한 레코드를 확인해야 한다.

## 실행한 검증

2026-10-13 최신 코드의 기존 `workers.assembly_asset_import` 기본 preview를 실행했다.
결과: exit0, DRY_RUN, record_count1, write_performed=false,
identity_review_confirmed=false, claim_publication=false. DB 환경변수가 없는 명시적
미사용 이름을 지정했으며 네트워크 요청이나 DB 연결·쓰기를 하지 않았다.

- 기존 receipt SHA-256: `77f7e8bc749b8fd21bd8bcf0fda1dcfa0807e7bbc38b5aced7ee3b33f5f42390`.
- 정규화 metadata hash: `082cb44a566e643bc0f52a237fa5d4ab72386acda7091929be9c2f127e130b71`.
- 이번 로컬 실행 기록: `dist/continuation-evidence/peti-one-record-preflight.json`.
- 기존 정책의 metadata 저장/AI 사용 허용 범위에서 공개 총계 필드만 확인했다.
  PDF·가족 세부정보·주소·항목 원문은 읽거나 새로 보존하지 않았다.

## 아직 확인하지 않은 것

과거 연결 제안은 Person `14ae67da-4a76-498b-977d-6992e3fa8e0c`와 공식
MONA `QWL7778X`이다. 현재 canonical roster·정책·동일 selector의 새 버전은
이번에 재조회하지 않았으므로 이 연결은 NOT_REVALIDATED다.
기존 proposal의 human_verified는 false다. 에이전트가 이를 true로 바꾸지 않았다.

## 다음 한 결정

사용자가 위의 정확한 공식 레코드를 확인하고 해당 인물과 일치한다고 검토했는지 확인한다.
그 확인은 공개 총계의 신원 연결에만 해당하며 신규 소스 권한·FACT 승격·서비스 배포 승인이 아니다.

실제 적용을 선택하면 현재 canonical 상태를 읽기 전용으로 먼저 확인하고 기존 경로의
policy registration → capture → reviewed LINK_PERSON → 별도 PUBLISH preview를 준비한다.
오래된 preview hash는 재사용하지 않는다. 각 쓰기의 실제 대상·변경 전후·복구 조건을
확인한 후에만 적용하며, 공개 Claim은 기존 계약의 CLAIM / asserted_as_true=false를 유지한다.

근거 규칙: `docs/roles/ROLE_MODEL.md`의 Curator and admin authority는 human_verified가
실제 사람의 검토를 나타내야 한다고 명시한다. 이 문서와 코드 검증은 그 사실을 대체하지 않는다.
