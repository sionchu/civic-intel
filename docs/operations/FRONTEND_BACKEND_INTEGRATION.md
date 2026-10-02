# 프론트엔드·백엔드 연결 및 진행안

2026-10-02. 현재 선택은 맥 외장 SSD의 정본 DB/API와 추후 Sites 화면이다.
이 문서는 실제 준비와 후속 제안을 구분한다. 서버 호출 경계와 기관 중심 화면은 구현했고,
최신 사용자 지시에 따라 과방위 출석요구 명단 두 건의 기관·인물 연결 후보를 준비했다.
터널·도메인·Sites를 생성하거나 Claim을 공개하지 않았다.

## 국감 우선 진행

사용자 지시(2026-10-02)에 따라 국감 화면에서 피감기관과 공식 출석요구 인물을 함께 연결한다.
정본은 계속 맥 외장 SSD이며, 기존 `/gukgam/2026/targets`와 Organization의
Claim·Evidence 화면을 재사용한다. 국회의원 명부를 피감자 명단으로 사용하지 않는다.

| 구분 | 국감에서의 의미 | 연결 기준 |
|---|---|---|
| 피감기관 | 공식 감사계획에 기재된 감사 대상 기관 | 위원회·일정·기관의 정확한 검토 연결과 공개된 감사대상 Claim |
| 기관증인 | 공식 기관증인 명단에 채택된 사람 | 별도 출석 명단과 해당 시점 직위·신원 근거 |
| 일반증인 | 공식 일반증인 명단에 채택된 사람 | 채택·변경·철회 기록과 신원 근거 |
| 참고인 | 공식 참고인 명단에 채택된 사람 | 별도 명단과 신원 근거; 증인과 구분 |
| 국회의원 | 감사를 수행하는 쪽의 인물 기록 | 기존 국회 명부; 피감기관·증인 수에 합산하지 않음 |

법 제7조의 감사대상 기관에는 국가기관, 법에 정한 지방자치단체와 공공기관 등이
포함된다. 실제 2026년 대상은 각 위원회 공식 계획서의 범위와 변경 사항을 확인해야 한다.
[국정감사 및 조사에 관한 법률 제7조](https://www.law.go.kr/LSW/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=1000279491).
기관장이라는 직함만으로 기관증인 채택을 추정하지 않는다. 출석 채택, 실제 출석,
감사 실시·결과와 감사계획의 대상 기재는 서로 다른 사실이다.

후속 공식 조회에서 과방위의 2026-09-22 기관증인 및 일반증인·참고인 명단이 확인됐다.
일반 명단에는 대상기관 열이 있어 과기정통부 ↔ 최주희(티빙 대표), 윤상현(CJ ENM 대표이사),
참고인 구교현 등을 요구 일시와 함께 연결할 수 있다. 소속 기업을 피감기관으로 추정하지 않는다.
원문 두 건으로 기관증인 직위 370행(이름 셀 369개), 일반증인 29행, 참고인 13행을 추출하고
정확한 페이지·행·원문 해시를 보존했다. 연구 후보이며 고유 canonical 인물 수가 아니다.
사람 검토·신원 연결·공개·실제 출석 확인은 미실행이다.
[원문·연결 후보 및 실행 순서](../research/gukgam_2026_science_witness_linkage_2026-10-02.md).

파이프라인과 위원회별 수집 순서는 [국감 수집 로드맵](GUKGAM_COLLECTION_ROADMAP.md)을 따른다.
첫 연결 검증은 과기정통부 47행이며, 과방위 전체 412행과 전국 coverage를 구분한다.
출처/관측 인입 → 신원 → Claim/Evidence 공개 → API/화면 순서다. Opus 화면 협업은
증인 전용 공개 DTO와 상태가 정해진 후 진행한다.
[증인 패킷·관측·비공개 검토 API](../architecture/GUKGAM_WITNESS_PACKET.md)는 R1에서 구현했다.
현재 DTO는 source-scoped 내부 검토용이다. 실제 자료는 DRAFT이고 신원·Claim 공개·화면 배포는
미실행이므로, 프론트엔드가 연구 JSON이나 admin API를 공개 데이터로 소비하지 않는다.

이전 읽기 전용 점검에서 맥 API의 Organizations와 공개 국감 대상은 각각 0건이었다.
기존 SSD의 298명은 국회의원이며, 피감 인물 목록이 아니다. 보유한 7개 위원회 검토 패킷은
57개 일정 행, 기관명 등장 390건, 서로 다른 출처 표기 359개를 담고 있다. 359개는
확정된 canonical 기관 수 또는 전국 전체 감사대상 수가 아니다. 모든 패킷은 증인·참고인
행을 포함하지 않는다. 공식 증인이 없다는 뜻도 아니다. 패킷 해시를 기존 인벤토리와
재검증했으며 이 이전 점검에서는 최신 공식 문서를 새로 수집하지 않았다.
후속 증인 두 건의 확인은 위의 별도 출석 명단 연구이며 계획서 최신성 점검을 대신하지 않는다.

연결 구조는 **위원회 → 감사 일정·피감기관 → 기관증인/일반증인/참고인 → 인물·소속 → 근거**다.
기관과 출석요구 인물의 검토 계약을 함께 준비한다.

1. 기존 국감 화면에서 피감기관을 먼저 보여주고, 공개된 대상 일정 수·위원회 수를 표시한다.
   기관 전체 수나 Person 수를 감사대상 수로 대신하지 않는다. 빈 데이터와 서비스 장애를 구분한다.
2. 7개 검토 패킷을 기준으로 맥의 정확한 대상 DB에 맞는 기관 연결 검토안을 준비한다.
   과거 staging의 41개 draft 연결과 70개 MOIS 제안은 검토 자료이며, 맥에는 기관이 없으므로
   과거 UUID를 그대로 적용할 수 없다. 기관 생성 권한과 정확한 연결의 사람 검토를 확인한다.
3. 허용된 효과별로 기존 source-specific CLI의 관측·기관 연결·Claim 공개를 나누고,
   각 전후 결과와 source/snapshot/observation 근거를 확인한다. 공통 persistence나 raw 저장소를 복제하지 않는다.
4. 준비한 실제 기관증인·일반증인·참고인 후보를 별도 출석 명단 계약으로 검토한다.
   기존 Source/Snapshot/Observation 인입·내부 review와 신원·공개 게이트를 재사용하고,
   원문 대상기관·소속·직위·출석요구 일시를 함께 연결한다. 기존 기관장 직위를 출석 명단으로 승격하지 않는다.
5. 같은 SSD API의 국감 화면을 검증한 뒤 기존 아래의 Workers·인증 연결·Sites 순서로 이어간다.

위원회 사이트의 반복 자동 수집은 현재 SourcePolicy상 차단돼 있다. 이전에 승인된 정확한
공식 파일의 사람 지원 경로를 유지한다. 화면 검증 이후 출석 명단 두 건만 유한한 operator
경로로 확인·추출했다. 운영 DB 쓰기, 실제 사람의 연결 승인, Claim 공개나 배포는 수행하지 않았다.
화면 QA용 일회성 로컬 DB의 테스트 관측·공개는 실제 SSD 데이터의 공개 증거가 아니다.
기존 국회 명부 파일럿과 보존된 Railway 자료는 유지한다. 상세 기준은
[국감 source contract](../architecture/GUKGAM_2026_SOURCE_CONTRACT.md)와
[현재 국감 실행 계획](../exec-plans/active/gukgam-2026-ontology-research.md)을 따른다.

이번 국감 변경은 전체 make verify를 통과했다(Python 862개, 선택적 PostgreSQL 4개 제외,
웹 34개, 타입·린트·Golden·아키텍처·standalone 빌드). Aside에서 로컬 테스트 DB의
빈 결과·공개 대상·조회 장애, 피감기관 버튼과 기관 상세 이동, 키보드 Evidence 펼치기를
확인했다. 실제 데스크톱 viewport 캡처 3장을 열어 검사했다. 모바일 API 부재와 긴 화면
캡처의 반복 이미지 때문에 전체 화면 검증은 미완료다. 테스트 서비스는 모두 종료했다.
실제 SSD의 피감기관 공개나 Sites 연결 증거는 아니다.
[국감 실행 receipt](../receipts/gukgam-priority-20261002.json).

## 권장 구조

```mermaid
flowchart LR
    U["사용자"] --> W["Sites: 기존 Next 화면"]
    W --> R["서버 전용 공개 조회"]
    R --> A["HTTPS · Cloudflare Access"]
    A --> T["맥에서 시작하는 Tunnel"]
    T --> API["맥: 읽기 전용 API"]
    API --> DB["외장 SSD: 정본 SQLite"]
```

브라우저는 Sites만 이용하고, Sites 서버가 맥의 공개 조회 API를 호출한다.
연결용 서비스 인증은 화면 번들에 포함하지 않는다. 사용자 로그인과 서버 연결 인증은
서로 다른 경계다. Sites는 나중에 owner-private으로 시작하며 검색 노출은 별도 결정이다.

Cloudflare Tunnel은 맥에서 외부로 연결하므로 직접 인바운드 포트를 열 필요가 없다.
Access의 Service Auth 정책은 허용한 서비스 토큰만 받도록 구성하는 제안이다.
이는 공식 기능을 조합한 설계이며 실제 Sites→Access→Mac 연결은 아직 검증하지 않았다.
[Tunnel 문서](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/),
[서비스 토큰 문서](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/).
계정·보유 도메인·서비스 비용은 현재 미확인이다. 이를 확인하고 정확한 접근 정책을
검토한 뒤 연결을 생성한다. 무인증 임시 터널은 이 안의 실행 경로에 포함하지 않는다.

## 연결 방식 선택지

| 방식 | 데이터 위치와 화면 | 장점 | 운영 조건 |
|---|---|---|---|
| A. 인증된 실시간 조회 — 권장 | 정본은 SSD, Sites가 맥 API를 조회 | 기존 API·Evidence 계약 재사용, 데이터 변경을 바로 반영 | 맥·SSD·인터넷 가동 필요, 도메인/Access 설정 필요 |
| B. 공개 DTO를 갱신하는 방식 | 정본은 SSD, 승인된 공개 결과만 Sites에 전달 | 맥이 쉬는 동안에도 마지막 공개 결과를 읽을 수 있음 | 별도 파생 조회 캐시·버전/갱신 시각·공개 선택 검증 필요, 실시간성 낮음 |
| C. 로컬 화면 먼저 검증 | 맥 또는 별도 로컬 화면에서 맥 API 조회, Sites는 이후 | 클라우드 연결 전 데이터와 화면부터 확인 | 외부 이용 불가, 실서비스 연결 증거가 되지 않음 |

현재 선택된 토폴로지와 가장 자연스럽게 이어지는 것은 A이며, 먼저 C 수준의 로컬 검증을
거친다. B는 맥의 상시 가동이 어렵다면 검토할 대안이다. B의 결과는 정본/원문 저장소가
아니며 SourceSnapshot이나 비공개 DRAFT를 복제하지 않는다. 아직 구현하거나 선택하지 않았다.

## 각 영역의 책임

| 영역 | 유지할 기준 | 다음 작업 |
|---|---|---|
| 프론트엔드 | 기존 DESIGN·Next 화면·DTO 유지 | 인물 목록→상세→Claim→Evidence→출처 흐름, 데이터 없음/장애/충돌 구분, 모바일·키보드 검증 |
| 서버 조회 | 기존 app/data.ts 하나로 연결 | 고정 API 주소, GET 제한, 서비스 인증, 리다이렉트 금지, 응답 시간 제한 |
| 백엔드 | 기존 FastAPI·Database/UoW·schema 0008 유지 | 출처·신원·공개 게이트 유지, 읽기 전용 API와 SSD 가용성 검증 |
| 수집 | 기존 승인된 deterministic CLI 사용 | 추후 수집 범위·예산을 별도로 승인하고 checkpoint/provenance 감사 |
| 공개 검토 | 기술적 적격성과 실제 공개 결정 구분 | 공개할 Claim의 정확한 목록과 근거를 준비하고 미해결 신원 충돌은 유지 |

현재 SSD는 국회 명부 299개 관측으로 만든 298명·298 DRAFT Claim과 검토 1건이다.
기존 Railway의 9,120명/기관 자료를 모두 SSD로 옮긴 상태는 아니다. 국회 명부 파일럿을
보존하고, 현재는 위의 국감 피감기관 연결을 우선한다. 다른 수집원을 붙이는 것은 별도 작업으로 정한다.
이 타깃으로 바꾸면 기관/ALIO 자료가 비어 있을 수 있으며 다른 DB로 조용히 우회하지 않는다.

현재 DRAFT는 API의 공개 Claim/Source 출력에서 제외된다. 따라서 이름 목록은 조회되지만
직위·학력·경력·재산 정보가 풍부한 인물 화면이 완성된 것은 아니다. 기존 데이터의
공개 선택과 출처별 보강 작업을 먼저 정하고, 없는 정보는 새로 만들어 채우지 않는다.

## 이번에 준비한 호출 경계

정본 프론트엔드의 app/data.ts에 server-only 경계를 추가했다.
기존 로컬 호출은 그대로 가능하며 HTTPS 서비스 연결을 위한 설정을 준비했다.

| 서버 설정 이름 | 용도 |
|---|---|
| CIVIC_API_URL | 조회 API의 고정 origin. 경로·query·fragment·URL 내 인증정보는 거절 |
| CIVIC_ACCESS_ORIGIN | 서비스 인증정보를 보낼 정확한 HTTPS origin |
| CIVIC_ACCESS_CLIENT_ID | 연결용 서비스 ID, 서버에서만 사용 |
| CIVIC_ACCESS_CLIENT_SECRET | 연결용 비밀값, Sites secret으로만 설정 |

기존 NEXT_PUBLIC_API_URL은 URL의 호환 입력만 유지한다. 서비스 비밀값을
NEXT_PUBLIC 변수에 넣지 않는다. 실제 키/토큰은 이번에 만들거나 읽지 않았다.
환경 설정은 연결 제공자가 확정된 뒤 native Sites 도구로 관리한다.

현재 호출 제한은 다음과 같다.

- 공개 Person/Organization/Source/ontology/국감/money GET 경로만 호출한다.
- ID는 UUID 경로 형태로 제한하고 admin/review/수집/쓰기 호출을 허용하지 않는다.
- 인증정보가 있으면 ID·secret·정확한 HTTPS origin이 모두 일치해야 한다.
- 리다이렉트를 따르지 않으며 8초 이내에 응답하지 않으면 서비스 오류를 반환한다.
- 서비스 인증을 사용하는 조회는 no-store다. 기존 무인증 로컬 목록은 60초 재검증을 유지한다.
- 맥/SSD/연결 장애는 기존 SERVICE_UNAVAILABLE로 전달한다. 이를 빈 목록이나 UNKNOWN으로 바꾸지 않는다.

이 제한은 Sites 내부 호출 경계다. 터널을 연결할 때에도 Mac/edge에서 GET 경로 제한과
Access 기본 거부 정책을 별도로 검증해야 한다. 앱의 호출 제한만으로 원격 API를 보호했다고
판정하지 않는다. API·DB·운영자 콘솔을 브라우저에 직접 연결하지 않는다.

## 구현 순서와 완료 조건

1. **서버 호출 준비:** 이번 작업. 실제 disposable HTTP 리다이렉트·timeout, 토큰 목적지
   불일치·미설정, 잘못된 경로, 기존 오류 의미와 DTO를 검증한다. 전체 코드 게이트를 통과한다.
2. **데이터 읽기 파일럿:** 현재는 위의 국감 피감기관 연결을 먼저 준비한다.
   기존 298 DRAFT의 공개 선택/근거는 별도로 유지한다.
   기술적 적격성을 공개 승인으로 쓰지 않는다. 생년월일 충돌 1건은 해결 근거가 생길 때까지
   제외한다. 공개한 항목만 동일 API에서 Claim→Evidence→Source를 읽는지 확인한다.
3. **화면 검증:** 기존 국감→기관→Evidence 흐름을 먼저, Person 화면은 이후 실제 데이터 상태로 확인한다. 긴 한국어, 빈 섹션,
   UNKNOWN/PARTIAL, 데이터 서비스 장애를 구분한다. Aside로 데스크톱/모바일/키보드를 검증한다.
4. **Workers 산출물:** 같은 Next 화면을 Vinext/Sites Vite 도구로 빌드한다.
   기존 standalone 개발 경로를 보존한다. 지금의 정적 호환성 12항목 통과는 이 빌드의
   완료 증거가 아니다. 사이트 ID를 임의로 만들거나 다른 화면용 스타터로 대체하지 않는다.
5. **실제 연결:** 도메인·계정·비용·소유권을 확인하고 Tunnel/Access의 구체 설정을 검토한다.
   승인된 서버 인증, 잘못된 토큰 거절, GET 외 요청 거절, admin/review 차단,
   맥/SSD 중단 시 오류 및 복구를 확인한다. 외부 API 주소 생성은 이 단계의 별도 효과다.
6. **Sites 제공:** 이후 배포 단계에서 native 등록/버전 저장/private 배포/status를 사용한다.
   같은 커밋의 화면→API→공개 Claim→Source 읽기가 검증된 뒤 제공한다.

1과 문서 준비 외 단계는 후속 작업이다. 데이터 공개, 새로운 비용/외부 접근과 실제
Sites 배포는 준비된 정확한 대상을 바탕으로 진행한다.

## 협업 배분

Codex MAIN이 백엔드·서버 연결·계약·데이터 게이트·최종 검증을 담당한다.
Opus는 기존 Person 화면의 정보 배치·읽기 흐름 개선을 맡길 수 있다. 전달 범위는
합성/공개 DTO와 DESIGN, Person 페이지·해당 CSS뿐이며 API키·DB·출판 권한은 전달하지 않는다.
수집 담당은 기존 source-specific CLI의 범위·정책·예산을 준비하고 MAIN이 별도로 실행한다.
검토 담당은 읽기 전용으로 회귀/권한/장애 상태를 확인한다.
이 배분은 다음 작업의 안이다. 이번에 Opus를 재호출하거나 새 수집 작업을 가동하지 않았다.

## 확인한 공식 자료

서버 호출 경계 단계의 실행 결과: 전체 make verify exit0, Python 862개 통과(선택적 PostgreSQL 4개 제외,
기존 SQLite 경고 6개), 웹 34개 통과(호출 경계 8개 포함), 타입·린트·Golden·아키텍처·
Next 16.3.8 standalone 빌드/자산 검증 통과. npm audit 결과 0건이다.
독립 코드·문서 검토에서도 결함을 찾지 못했다. Vinext 정적 검사도 12항목 통과했으나
Workers 빌드·실연결·화면 검증의 증거는 아니다. 실제 실행 명령과 미실행 항목은
[호출 경계 receipt](../receipts/web-api-bridge-20261002.json)에 기록했다.

- [Next 서버·클라이언트 경계](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [OpenAI Sites SDK](https://github.com/openai/sites)
- [Vinext](https://github.com/cloudflare/vinext)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Access 서비스 인증](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/)

현재 SDK/MCP 조사와 SSD 런타임의 이전 증거는
[SSD 운영 기록](MAC_SSD_SITE.md) 및 [실행 receipt](../receipts/mac-ssd-site-20261002.json)에 보존한다.
