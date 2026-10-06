# Evidence Graph prior art — 외부 프로젝트·학술 근거 (2026-10-07)

조사일: 2026-10-07. 저장소 활동일은 GitHub API `pushed_at`(2026-10-07 조회) 기준. 확인 못 한 항목은 `UNVERIFIED`.
판단 전제: 기존 PostgreSQL(Person / Organization / Claim[S-P-O + qualifiers, valid_from/valid_to] / ClaimEvidence / Source / SourceSnapshot / FeederObservation) + source-policy·publication gate 유지. **병행 truth store·graph DB 추가 금지.**

## 요약 결정표

| 프로젝트 | 결정 | 한 줄 이유 |
|---|---|---|
| FollowTheMoney (FtM) | **ADAPT** | Interval 계열(Membership/Directorship/Ownership/Occupancy 등) 어휘·필드를 predicate/qualifier 사전으로 차용. 라이브러리·저장소는 도입 안 함 |
| Popolo | **ADAPT** | Membership(person, organization, post, role, on_behalf_of, start/end) 구조를 정치 소속 Claim 템플릿으로 차용 |
| OpenSanctions (+yente, nomenklatura) | **REFERENCE** (statement 모델·ER 판정 방식) / 데이터는 REJECT(라이선스) | CC BY-NC 4.0 → 공익이라도 재배포·상업성 리스크. statement·judgement 설계만 참고 |
| LittleSis | **REFERENCE** | 12개 relationship category·start/end/is_current 설계 참고. 위키형 편집·GPL 코드는 채택 안 함 |
| Oligrapher | **REFERENCE** | 스토리형 그래프 시각화 UX 참고. GPL-3.0, React/Redux 종속 |
| OCCRP Aleph / OpenAleph | **REJECT** | Elasticsearch 기반 별도 저장소 = 병행 truth store. Aleph 레거시는 2025-12-31 유지보수 종료 |
| Open Civic Data | **REFERENCE** | `ocd-division` ID(country-kr 존재)를 선거구/행정구역 crosswalk 후보로 참고 |
| EveryPolitician (2026 재출범) | **REFERENCE** | Wikidata 기반 PEP. CC BY-NC → discovery 용도로만 |
| BODS v0.4 | **ADAPT** | 소유·지배 interest 코드리스트, statementDate, source.type/assertedBy/retrievedAt를 Ownership/Control Claim qualifier로 차용 |
| Wikidata | **ADAPT (discovery-only crosswalk)** | QID를 외부 식별자로 저장, P39/P69/P102/P108/P580/P582는 후보 발견용. 단독 증거로 게시 금지 |
| OpenCorporates | **REFERENCE** | ODbL share-alike + 한국 커버리지 빈약(KR openness 25/100) |
| 대한민국 인맥지도 (akngs/smallworld) | **REFERENCE (반면교사)** | Wikidata 공통 학교·출생지로 학연·지연 "관계"를 추론 → 우리 모델에서 금지할 패턴의 사례 |
| 열린국회정보 Open API 기반 OSS | **ADAPT (feeder)** | 1차 공공출처. open-assembly-mcp(Apache-2.0)는 엔드포인트 카탈로그 참고 |
| teampopong / OpenWatch (선거·정치자금) | **REFERENCE** / OpenWatch 데이터는 조건부 | popong은 2014–2018 중단. OpenWatch CC BY-SA 4.0 → 원출처(선관위) 우선 수집 |
| BigKinds 관계도 | **REJECT (증거로서)** | 기사 내 공출현 빈도 = 관계 아님 + 기사 저작권·재배포 금지 |

---

## Part A — 프로젝트별 상세

### 1. LittleSis
- repository: https://github.com/public-accountability/littlesis-rails · current_activity: 활발 (pushed 2026-10-05, 미보관)
- license: GPL-3.0 · data_license: CC BY-SA 4.0 (API 문서 명시)
- ontology: Entity(Person/Org) + extension 타입(Business Person, Public Company, Political Candidate 등) + Relationship(12 category)
- person/organization_model: 단일 `entity` 테이블 + `primary_ext` + 확장 속성
- membership/relationship_model: Relationship 1개 = 두 entity + category_id(1–12; Position, Education, Membership, Family, Donation/Grant, Service/Transaction, Lobbying, Social, Professional, Ownership, Hierarchy, Generic — 앞 7개 정의는 공식 help 검색결과로 확인, 뒤 5개 명칭은 일반 알려진 값으로 정의 원문 미확인 `UNVERIFIED`), description1/2(직함), amount/currency
- temporal_model: start_date, end_date, is_current(null=모름) — "모름"을 명시적으로 3값 처리
- provenance_model: relationship/entity 단위 reference(URL) 첨부(세부 스키마 `UNVERIFIED`), 위키식 편집 이력
- entity_resolution: 수동(편집자 병합) 중심 `UNVERIFIED`
- bulk_data / api: bulk 페이지 존재(봇 차단으로 형식 미확인) / JSON REST, 키 불필요, rate limit
- graph_visualization: Oligrapher · korea_support: 없음
- reusable_code: 낮음(GPL, Rails) · reusable_model: relationship category 분류, is_current 3값
- limitations: P+P 관계(Social/Professional)를 직접 사실로 저장 → 우리 원칙(P↔P는 projection)과 충돌
- **adoption_decision: REFERENCE** — 카테고리 체계를 predicate 분류 점검표로만 사용.

### 2. Oligrapher
- repository: https://github.com/public-accountability/oligrapher · activity: pushed 2026-09-20
- license: GPL-3.0 · data_license: 해당 없음(사용자 맵)
- ontology/model: 노드·엣지·캡션·annotation(스토리 슬라이드) — 사실 모델 아님
- temporal/provenance/ER: 없음(시각화 레이어) · bulk/api: 없음 · visualization: SVG/JPEG export, 스토리 시퀀스
- korea_support: 없음 · reusable_code: GPL로 직접 내장 부담 · reusable_model: "annotation 스토리" UX
- **adoption_decision: REFERENCE** — 게시용 설명형 그래프 UX 참고, 렌더러는 projection 결과만 소비.

### 3. FollowTheMoney (FtM)
- repository: https://github.com/opensanctions/followthemoney (alephdata → opensanctions 이관) · activity: pushed 2026-10-05
- license: MIT · data_license: 해당 없음(스키마)
- ontology: Thing(Person, Organization, Company, PublicBody, LegalEntity, Position…) / Interval(관계·이벤트) 계층
- person/organization_model: Person, Organization, Company, PublicBody 스키마, 다중값 property
- membership_model: `Membership(member, organization, role)`, `Directorship(director, organization, role)`, `Employment(employee, employer)`, `Occupancy(holder, post, status, constituency, politicalGroup, electionDate, periodStart/End, declarationDate)` + `Position`
- relationship_model: Ownership(owner, asset, percentage), Family, Associate, Representation, UnknownLink 등 — 관계 자체가 엔티티(reified)
- temporal_model: Interval 공통 startDate/endDate/date, 그 외 retrievedAt, modifiedAt
- provenance_model: Interval의 sourceUrl, publisher, publisherUrl, proof(문서 엔티티), recordId; 저장 레벨은 statement 모델(dataset, first_seen/last_seen)
- entity_resolution: nomenklatura(아래) · bulk/api: 스키마 YAML, Python 라이브러리
- graph_visualization: Aleph/OpenAleph 쪽 · korea_support: 언어 중립, 한글명 다중 name 가능
- reusable_code: 스키마 YAML 참조용(MIT) · reusable_model: **Occupancy의 periodStart/End(임기) vs startDate/endDate(실제 재직) 구분**, reified 관계
- limitations: 엔티티 전체를 FtM으로 저장하면 병행 store가 됨
- **adoption_decision: ADAPT** — predicate 사전·qualifier 이름을 FtM에 정렬(export 매핑 가능), 저장은 기존 Claim.

### 4. OCCRP Aleph / OpenAleph
- repository: https://github.com/alephdata/aleph (pushed 2026-02-20) · OpenAleph: https://openaleph.org (DARC soft fork, MIT, 5.0.0 2025-09-01)
- current_activity: Aleph OSS는 "sunsetted", 유지보수 2025-12-31 종료, OCCRP는 Aleph Pro로 이전. OpenAleph는 활동 중
- license: MIT · data_license: 인스턴스별
- ontology/모든 model: FtM 그대로 · provenance: collection 단위 + 문서 ingest
- entity_resolution: xref(교차매칭) · bulk/api: REST API, 인스턴스별
- graph_visualization: network diagram · korea_support: 문서 OCR/ingest 수준 `UNVERIFIED`
- limitations: Elasticsearch+Postgres 별도 플랫폼 = 병행 truth store
- **adoption_decision: REJECT** — 아키텍처 금지 조건 위반; FtM 호환성만 확보.

### 5. OpenSanctions (+ yente, nomenklatura)
- repository: https://github.com/opensanctions/opensanctions · yente(pushed 2026-10-05, MIT) · nomenklatura(pushed 2026-10-01, MIT)
- data_license: **CC BY 4.0 NonCommercial**(비상업), 상업은 별도 라이선스/Screening API
- ontology: FtM · person_model: Person + topics(role.pep, role.rca 등)
- membership_model: Occupancy + Position (PEP) · relationship_model: Family/Associate/Ownership/Directorship
- temporal_model: Occupancy start/end + statement first_seen/last_seen
- provenance_model: **statement 모델** — (entity_id, prop, value, dataset, first_seen, last_seen …) 속성값 하나하나 출처 추적
- entity_resolution: nomenklatura — inverted-index blocking(ngram/음역) → 스코어링 → **사람 판정(positive/negative/unsure)** → 판정 그래프 connected component → canonical ID(`NK-…`), statement 보존으로 병합 취소 가능
- bulk_data: 데이터셋별 CSV/FtM JSON · api: yente(/match, /search, OpenRefine reconciliation)
- korea_support: KR 연관 3,422 엔티티, PEP 2,486(정치인 2,020). 한국 공식 출처는 1개 — `kr_assembly`(open.assembly.go.kr 기반, 현직 300명, 월간, 최종 2026-09-15 처리). 역대 재임 이력 없음
- reusable_code: nomenklatura 판정/resolver 설계(MIT) · reusable_model: statement+judgement
- limitations: NC 라이선스, 한국 커버리지는 현직 의원+Wikidata 위주
- **adoption_decision: REFERENCE** — ER judgement 테이블 설계와 statement 출처 모델만 차용; 데이터 재게시 금지(필요 시 discovery 대조용).

### 6. Popolo
- repository: https://github.com/popolo-project/popolo-spec · activity: pushed 2023-02-13 (사실상 정체, 표준은 안정)
- license: 저장소 license 필드 null (`UNVERIFIED`) · data_license: 해당 없음
- ontology: Person, Organization, Membership, Post, Motion/VoteEvent, Area, ContactDetail
- membership_model: `Membership(person_id|member, organization_id, post_id, role, on_behalf_of_id, area, start_date, end_date, label)` — member와 organization/post 없이는 존재 불가
- relationship_model: P↔P 없음(소속을 통해서만) — 우리 원칙과 일치
- temporal_model: start/end date(부분 날짜 허용) · provenance_model: `sources` 배열(링크)
- entity_resolution/bulk/api/visualization: 없음(스펙) · korea_support: 언어 중립
- reusable_model: **Post(의석·직위) 분리**, on_behalf_of(소속 정당 대리)
- **adoption_decision: ADAPT** — 정치 소속 Claim을 Popolo Membership/Post 형태로 qualifier 표준화.

### 7. Open Civic Data (OCD)
- repository: https://github.com/opencivicdata (docs pushed 2026-04-22, ocd-division-ids pushed 2026-09-26)
- license: docs null, division-ids "Other" (`UNVERIFIED` 세부)
- ontology: Popolo 파생 Person/Organization/Membership/Post + Bill/Vote/Event(OCDEP)
- division: `ocd-division/country:kr/...` — country-kr에 provinces, cities, single_member_constituencies(국회 지역구) CSV 존재
- temporal/provenance: Popolo식 start/end + sources · ER: 없음 · bulk/api: 미국 Open States 중심
- **adoption_decision: REFERENCE** — 선거구/지역 ID crosswalk 후보(선거구 개편 이력은 직접 관리 필요).

### 8. EveryPolitician
- status: mySociety가 2019 중단 → **2026 OpenSanctions가 재출범**(everypolitician.org, 저장소 opensanctions/everypolitician.org). PoliLoom(LLM 추출 + 사람 검토 후 리뷰어 OAuth로 Wikidata에 기록)
- data_license: CC BY 4.0 NonCommercial · ontology: FtM/Wikidata 기반 PEP (P39 position)
- korea_support: 국가별 페이지 있으나 한국 세부 수치 `UNVERIFIED`
- limitations: Wikidata 품질 의존, NC 라이선스
- **adoption_decision: REFERENCE** — discovery 후보 목록, 사람검토 워크플로 참고. 게시 근거로 쓰지 않음.

### 9. Beneficial Ownership Data Standard (BODS)
- repository: https://github.com/openownership/data-standard · activity: pushed 2026-09-02 · 현행 v0.4
- license: 저장소 "Other" `UNVERIFIED` · data_license 권고: Public Domain/Open Definition 적합 라이선스
- ontology: recordType = entity / person / relationship
- relationship_model: `subject`(entity), `interestedParty`(person/entity/unspecified), `interests[]{type(26개 코드: shareholding, votingRights, board 관련, seniorManagingOfficial 등), directOrIndirect, share(정확/범위), startDate, endDate}`
- temporal_model: statementDate(필수, 선언일) + interest start/end — **"언제 선언됐나" vs "언제 유효했나" 분리**
- provenance_model: source.type(selfDeclaration, officialRegister, thirdParty, primaryResearch, verified), assertedBy, retrievedAt, annotations(JSON pointer)
- korea_support: 없음(한국 BO 등록부 공개 없음) · bulk/api: 표준만
- **adoption_decision: ADAPT** — Ownership/Control Claim의 qualifier(share 범위, direct/indirect, source.type)로 차용.

### 10. Wikidata (한국 정치인)
- access: SPARQL(query.wikidata.org), 덤프, REST · data_license: CC0
- properties: P39 position held(+qualifier P580 start time, P582 end time, P2937 parliamentary term, P768 electoral district, P4100 parliamentary group), P69 educated at, P102 member of political party, P108 employer, P106 occupation
- 한국 ID: **P8155 Republic of Korea Parliamentarian Society ID(대한민국헌정회)** 확인; 국회 열린국회정보 의원코드 전용 property는 확인 못 함(`UNVERIFIED`). 기타 P5034 National Library of Korea ID
- 예: Q14850694 "Member of the National Assembly of South Korea", Q10855898(김진표)에서 P39+P2937+P768 사용 확인
- provenance: statement별 references(P854 등) 선택적 — 다수 미출처
- limitations: 누락·편향·편집 분쟁, 출처 없는 학력/출생지 다수
- **adoption_decision: ADAPT (discovery-only crosswalk)** — QID를 외부 ID로 저장, 후보 생성·대조용. Claim 게시는 1차 출처 증거가 있을 때만.

### 11. OpenCorporates
- data_license: ODbL(share-alike, attribution). API: Permitted User 무료 share-alike 키 / 유료 non-share-alike
- ontology: Company, Officer(직함·start/end), 일부 control statement · provenance: 레지스트리 URL·retrieved
- korea_support: jurisdiction `kr` 존재하나 openness 25/100, 등기부(iros) 전체 공개·재사용 불가
- **adoption_decision: REFERENCE** — 한국 회사 데이터는 DART/등기 등 국내 1차 출처로 직접.

### 12. 대한민국 인맥지도 (Smallworld)
- repository: https://github.com/akngs/smallworld (site akngs.github.io/smallworld) · activity: pushed 2023-01-04(정체) · license: null(`UNVERIFIED`)
- data: Wikidata 등재 한국 국적 인물(+배우자/부모/자녀). 학교·출생지·소속·직위 표시
- relationship_model: 지연·학연·혈연을 **공통 속성에서 추론**, 혈연 탐색기 구현. 저자 스스로 관계 데이터 부족으로 노드 단절 언급
- **adoption_decision: REFERENCE (반면교사)** — 동문/동향을 사실 관계로 게시하지 말 것. 공통 소속은 projection으로만, "관계" 라벨 금지.

### 13. 열린국회정보 Open API 기반 오픈소스
- 원천: open.assembly.go.kr Open API(국회의원 인적사항, 역대 국회의원 인적사항, 발의법률안, 표결, 위원회). 파라미터 Type/pIndex/pSize, 키 필요
- kyusik-yang/open-assembly-mcp: Apache-2.0, pushed 2026-09-29 (법안·의원·표결)
- WooilJeong/PublicDataReader(공공데이터 Python 래퍼, 국회 포함 여부 `UNVERIFIED`), yybmion/public-apis-4Kr(카탈로그)
- 이용조건: 공공누리 유형 등 API별 라이선스 `UNVERIFIED` — API별 확인 필요
- **adoption_decision: ADAPT (feeder)** — FeederObservation 원천으로 직접 수집; 외부 OSS 코드는 엔드포인트 참고만.

### 14. 선거 데이터 (teampopong, OpenWatch)
- teampopong: popong-models(SQLAlchemy 한국 정치 모델, BSD-3, pushed 2014-10-24), data-for-rnd(1–19대 후보자 CSV, 선관위, pushed 2016), data-assembly(pushed 2018, license null), crawlers(선관위 크롤러). 사실상 중단
- OpenWatch(openwatch.kr): 국회의원 기본·경력·재산·표결, 정치후원금 고액기부자(2008–2024, 선관위 정보공개청구 가공), API 제공, **CC BY-SA 4.0**. 저장소 `UNVERIFIED`
- 원천: 중앙선관위 선거통계시스템/공공데이터포털 API(세부 조건 `UNVERIFIED`)
- **adoption_decision: REFERENCE** — popong-models 스키마 참고. OpenWatch는 SA 의무와 개인정보(기부자) 위험 → 선관위 원출처 우선, 고액기부자 개인은 publication gate 엄격 적용.

### 15. BigKinds 관계도
- 운영: 한국언론진흥재단. 관계도 = 검색 상위 100건 기사에서 개체명(인물·기관·장소) **동일 기사 공출현 빈도**로 엣지 생성
- API: 별도 신청 OPEN API, 기사 전재·복제·배포 금지(저작권). 연구 사례: 국회의원 공출현 네트워크(박진우 2022, 서지 `UNVERIFIED`)
- **adoption_decision: REJECT (증거로서)** — 기사 탐색(discovery) 링크만 허용, 공출현은 Claim 아님.

---

## Part B — 학술 근거 (요약)

검증 범위: 1–6번(Breiger, McPherson 외, Kivelä 외, Padgett & Ansell, Mizruchi, Faccio)은 널리 인용되는 고전 서지로, 권·호·쪽은 저자 지식 기준이며 이번 세션에서 웹으로 재확인하지 않았다(`NOT_WEB_VERIFIED`). 7번 Fowler는 웹 확인. 8–9번 한국 문헌은 KCI/DBpia/IDEAS에서 확인.

1. **Breiger, R. L. (1974). The Duality of Persons and Groups. *Social Forces* 53(2):181–190.**
   사람–집단 2-mode(bipartite) 행렬에서 P↔P, G↔G 네트워크는 곱(projection)으로 유도된다.
   → 수집 대상은 Person–Organization 소속(2-mode)이다. P↔P "관계"는 저장하지 않고 투영으로 계산한다. 투영 가중치(공동 소속 수, 기간 중첩)는 계산값이다.

2. **McPherson, Smith-Lovin & Cook (2001). Birds of a Feather: Homophily in Social Networks. *Annual Review of Sociology* 27:415–444.**
   유사성(지위·학력·지역)이 연결을 만들지만 유사성 자체가 연결은 아니다(baseline vs inbreeding homophily).
   → 동문·동향은 "속성 공유"일 뿐이다. 관계로 표시하지 않는다. 속성 Claim(학력·출생지)과 관계 Claim을 분리한다.

3. **Kivelä, M. et al. (2014). Multilayer networks. *Journal of Complex Networks* 2(3):203–271.**
   관계 종류·시간별 레이어를 분리하고 레이어 간 결합을 명시하는 일반 틀이다.
   → predicate별(공직·정당·이사회·지분·가족) 레이어를 유지한다. 시각화에서 레이어를 합칠 때 원 레이어를 보존한다. 시간 슬라이스도 레이어로 다룬다.

4. **Padgett, J. F. & Ansell, C. K. (1993). Robust Action and the Rise of the Medici, 1400–1434. *American Journal of Sociology* 98(6):1259–1319.**
   혼인·경제 등 이질적 관계망이 분리되어 있고, 그 구멍을 잇는 위치에서 권력이 나온다.
   → 관계 유형을 하나의 "인맥" 점수로 합치지 않는다. 가족(혼인)·사업 레이어를 별도 근거로 유지한다. 브로커 위치는 투영 분석 결과로만 제시한다.

5. **Mizruchi, M. S. (1996). What Do Interlocks Do? An Analysis, Critique, and Assessment of Research on Interlocking Directorates. *Annual Review of Sociology* 22:271–298.**
   겸임이사는 공모·흡수(cooptation)·정보·경력 등 여러 원인과 결과를 가지며, 인과 해석은 어렵다.
   → 수집 대상은 Directorship(회사, 직위, 기간, 공시 출처)이다. 회사↔회사 interlock은 투영이다. "유착" 같은 해석 라벨을 붙이지 않는다.

6. **Faccio, M. (2006). Politically Connected Firms. *American Economic Review* 96(1):369–386.**
   대주주·임원이 의원·장관이거나 이들과 "가까운" 기업을 정치연결기업으로 정의했다(47개국).
   → 정의 요소는 공직 재임 기간과 기업 임원·지분 보유 기간의 **겹침**이다. 기간 qualifier가 필수다. "친분"류 연결은 증거 등급을 분리하거나 수집하지 않는다.

7. **Fowler, J. H. (2006). Connecting the Congress: A Study of Cosponsorship Networks. *Political Analysis* 14(4):456–487;** 같은 해 *Social Networks* 28(4):454–465.
   공동발의를 의원 간 연결로 보고 connectedness 지표를 제안했다.
   → 공동발의·표결은 의원–법안 2-mode 사실(Bill sponsorship Claim)로 저장한다. 의원↔의원 연결은 투영이다.
   **Poole & Rosenthal (1985). A Spatial Model for Legislative Roll Call Analysis. *AJPS* 29(2):357–384** (NOMINATE): 표결 유사도는 이념 위치 추정이지 관계가 아니다. 서지는 저자 지식 기준이며 이번 세션에서 웹 확인하지 않음.

8. **한국 정치 엘리트 네트워크 (검증됨)**
   - 엄기홍·윤장원 (2013). 한국 정치과정에서의 학연, 부패의 시작인가?: 제19대 국회의원선거 정당 후보자 공천에 대한 경험적 분석. *한국정당학회보* 12(3):29–47. → 학연은 공천 결과 변수와 연결되는 "속성"으로 다룬다. 관계로 보지 않는다.
   - 박찬무·장원철 (2017). 17대 국회의 공동법안발의에 관한 네트워크 분석. *응용통계연구* 30(3):403–415. ERGM 분석에서 같은 정당 효과가 가장 컸다. → 정당 소속 기간 Claim이 필수 통제 변수다.
   - 이지연·조현주·윤지원 (2014). 제18대, 19대 대표발의안을 중심으로 본 국회의원 및 상임위원회의 입법활동에 대한 네트워크 분석. *디지털융복합연구* 12(2):11–25. bipartite projection 방법을 썼다.
   - 김근세·박지숙·장사무엘 (2024). 이승만 행정부 파워엘리트의 구성과 변화: 장·차관을 중심으로. *한국행정연구* 33(4):1–50. 지연·학연·직연(경력)을 분석했다. 직연은 경력 Membership에서 유도된다.

9. **한국 기업 엘리트 / 사외이사 (검증됨)**
   - 김용민·박기성 (2004). 한국 대기업 최고경영자의 지연과 학연. *산업관계연구* 14(2):77–96. 소유주–CEO 동향 43.2%, 고교 동문 13.1%였다.
   - Shin, Hyun, Oh & Yang (2018). The effects of politically connected outside directors on firm performance: Evidence from Korean chaebol firms. *Corporate Governance: An International Review* (DOI 10.1111/corg.12203; 권·호 `UNVERIFIED`). 전직 관료 출신 사외이사가 효과를 주도했다. → "전직 공직 → 사외이사" 경력 전이를 시간순 Claim으로 수집할 근거다.
   - 박선현 (2021). 한국기업 사외이사 네트워크에서의 끊어진 연결 복구. *전략경영연구* 24(3):1–32. 2002–2011년 1,382개사를 분석했다. 학연·지연과 관료 출신 네트워크가 재구축되었다.
   - Kim, D. S. & Lee, S.-H. (2024). Board political connections and financial fraud: The case of business groups in South Korea. *Asia Pacific Journal of Management* 41(4):2119–2153. 정치 연결도가 높을수록 회계부정이 적었다. → 연결이 곧 비리라는 프레이밍을 금지할 근거다.

## Part C — 우리 모델에 대한 함의

1. 1차 수집 단위는 **Person–Organization/Post 소속 Claim**(2-mode)이다. Person↔Person은 가족·혼인처럼 출처가 직접 진술한 경우만 Claim으로 두고, 나머지는 결정론적 projection으로 계산한다.
2. predicate 사전은 FtM(Membership/Directorship/Employment/Occupancy/Ownership/Family)과 Popolo(Membership+Post+on_behalf_of)에 이름을 정렬한다. 그러면 저장 없이 export 매핑만으로 호환된다.
3. 시간은 **세 축으로 분리**한다. valid_from/valid_to(실제 재직), 임기(periodStart/End, P2937 대수), 선언·관측일(statementDate / FeederObservation.observed_at). 미상은 null + `is_current` 3값으로 표현한다.
4. Ownership/Control에는 BODS qualifier(share 정확/범위, directOrIndirect, interest type, source.type)를 쓴다.
5. Source에 BODS `source.type`(officialRegister / selfDeclaration / thirdParty / primaryResearch)과 같은 출처 등급을 두고 publication gate 입력으로 쓴다.
6. 엔티티 해석은 nomenklatura 방식을 쓴다. 사람 판정(positive/negative/unsure)을 별도 테이블에 저장하고, 원 Claim은 불변으로 두어 병합을 되돌릴 수 있게 한다. 자동 매칭은 후보 생성까지만 한다.
7. Wikidata QID, P8155(헌정회 ID), OCD division ID, 국회 의원코드, DART 고유번호는 **외부 식별자 crosswalk**로만 저장한다. Wikidata 값은 discovery 후보이고, 게시 근거는 1차 출처 ClaimEvidence여야 한다.
8. 학연·지연(같은 학교·출생지)은 Person 속성 Claim으로 저장하고, 화면에서는 "공통 속성"으로 표기한다. "인맥/관계" 라벨과 엣지는 금지한다(Smallworld 반면교사, homophily 문헌).
9. 뉴스 공출현(BigKinds 등)과 표결 유사도는 Claim이 아니다. 기사는 Source discovery 링크로만 쓴다.
10. NC·SA 라이선스(OpenSanctions/EveryPolitician CC BY-NC, OpenCorporates ODbL, OpenWatch·LittleSis CC BY-SA)의 데이터는 source-policy에서 "대조·발견 전용, 재게시 금지" 등급으로 둔다. 공공 원출처(열린국회정보, 선관위, DART)를 우선한다.
11. 정치연결 분석(Faccio 유형)은 Occupancy 기간과 Directorship/Ownership 기간이 겹치는지를 계산하는 projection으로 제공한다. 해석 라벨(유착·특혜)은 붙이지 않는다(Kim & Lee 2024).
12. 시각화(Oligrapher 유형)는 게시 게이트를 통과한 projection만 소비하는 읽기 전용 레이어로 둔다. 레이어(predicate)·기간 필터와 엣지별 근거 링크를 필수로 한다.

## 주요 출처
- LittleSis API https://littlesis.org/api/ · OpenSanctions licensing https://www.opensanctions.org/licensing/ · KR https://www.opensanctions.org/countries/kr/ · kr_assembly https://www.opensanctions.org/datasets/kr_assembly/
- 중복제거 https://www.opensanctions.org/articles/2021-11-11-deduplication/ · statements https://www.opensanctions.org/docs/statements/
- EveryPolitician https://everypolitician.org/ · PoliLoom https://www.opensanctions.org/articles/2026-03-24-poliloom/
- Aleph 공지 https://github.com/alephdata/aleph · OpenAleph https://openaleph.org/blog/2025/openaleph-commits-to-the-commons/
- FtM Interval/Occupancy https://followthemoney.tech/explorer/schemata/Interval/ · Popolo https://www.popoloproject.com/specs/membership.html
- BODS https://standard.openownership.org/en/latest/standard/reference.html · OCD KR https://github.com/opencivicdata/ocd-division-ids/tree/master/identifiers/country-kr
- Wikidata P8155 https://www.wikidata.org/wiki/Property:P8155 · Smallworld https://akngs.github.io/smallworld/2018/09/08/welcome.html
- OpenWatch https://docs.openwatch.kr/ · teampopong https://github.com/teampopong · open-assembly-mcp https://github.com/kyusik-yang/open-assembly-mcp
- KCI: ART002241838, ART003159421, ART001851529, ART002791613 · DBpia NODE01455409 · IDEAS s10490-023-09902-8 · Wiley 10.1111/corg.12203
