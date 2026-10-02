# 사이트·데이터·Claude Opus 협업 계획

상태: 2026-10-02 사용자가 1번 국회 파일럿 통합을 선택했다. 점검 당시 상태와 선택지를 보존한다.
실제 작업은 [승인된 실행 계획](../exec-plans/active/assembly-site-pilot.md)에서 진행하며,
배포·source·identity·publication의 각 효과와 검증 결과를 구분한다.
기준 커밋: `0eb326d616002a96e0ddbdd31e982a83a483664d`.

## 확인된 현재 상태

| 영역 | 확인 결과 | 남은 확인 |
|---|---|---|
| 코드 | `codex/architecture-current-master`의 수집·구조 개편 완료. 로컬 `origin/master` 대비 17커밋 앞섬 | 이 기준 커밋의 원격 CI와 배포 연결 |
| 로컬 원본 | `master`에는 별도 이력과 사용자 수정 `packages/domain/contracts.py`가 있음 | 출시 기준은 원본을 덮어쓰거나 무조건 병합하지 않고 확정 |
| 맥 SSD 수집 | 읽기 전용 재확인: schema0008, 국회 현역 명부 299관측, 3스냅샷, checkpoint3, SUCCESS 1회 | 이 DB의 Person·Claim·Organization은 모두 0 |
| Railway staging | PostgreSQL·API·Web의 최신 배포 상태 SUCCESS. 기존 Web 루트 GET200 | 실제 배포 SHA, 현재 DB schema·내용, 현재 UI 수용 검증 |
| Railway production | 서비스 0, bucket 0 | 운영 환경 생성·비용·공개 범위 결정 |
| 프론트엔드 | Home, People, Person, Organization/MONEY, Gukgam 및 제한된 운영자 화면이 구현됨 | 현재 커밋의 실제 화면·상호작용 검증 |
| Claude | Windows Claude Code2.1.281 설치, claude.ai 로그인 확인 | 실제 Opus 호출·가용 모델·사용량은 미검증 |
| Aside | CLI·guide 정상. account 조회는 daemon auth challenge 실패; 데몬 없음 | 실제 데스크톱/모바일 화면 검증 미완료 |

현재 staging Web: <https://web-staging-efe2.up.railway.app>.
API와 PostgreSQL에는 공개 도메인이 없다. 배포 상태 SUCCESS와 HTTP200은 렌더링 검증이 아니다.
API의 마지막 성공 배포는 2026-09-23, Web은 2026-09-20이다. 배포 SHA는 connector 결과에 없었다.
작업 기준 커밋에 대한 `gh run list --commit`은 실행 이력을 반환하지 않았다.
이전 전체 로컬 검증 결과는 [완료 기록](../receipts/mac-collector-bounded-20261002.md)에 있고,
이번 점검에서는 테스트를 재실행하지 않았다.

## 데이터가 사이트에 도달하는 경로

맥 SSD의 SQLite와 Railway의 사이트용 PostgreSQL은 다른 DB다.
현재 299관측이 사이트에 연결됐다고 볼 수 없다. 국회 audit exporter는 검토 보고서를 만들 뿐,
전체 canonical graph를 옮기는 transfer/import 명령이 아니다.

권장 경로는 기존 source-specific worker를 승인된 사이트용 PostgreSQL 대상에서 한 번 실행하는 것이다.
기존 맥 수집본은 보존하고 검토·비교에 재사용한다. SQLite 파일을 PostgreSQL에 복사하거나 운영 DB를
교체하지 않는다. 배포 문서의 canonical loading 경로를 그대로 쓴다.

1. 대상 DB의 schema, 기존 레코드·충돌, 현재 source policy, 백업/복구와 sole-writer 조건을 읽기 전용으로 확인한다.
2. 대상·feeder·scope·policy·키 보관 위치·요청/시간 예산을 고정한 국회 수집 요청을 만든다.
   맥 SSD 1회 수집 승인은 이 PostgreSQL 대상의 쓰기 승인이 아니다.
3. 승인 범위에서 기존 `civic observe assembly`로 source/snapshot/observation과 checkpoint를 원자적으로 저장한다.
   제안 예산은 기존 증명된 100건/page, 최대8요청, 최소1초 간격, fetch120초, hard stop180초다.
   현재 맥 전용 launcher의 sandbox/target은 그대로 재사용할 수 없으므로 대상 실행 환경의 제한과 중단을 다시 검증한다.
4. coverage·중복·출처·개인정보 감사 후 기존 `civic materialize assembly`를 별도 단계로 실행한다.
   provider identity 규칙을 충족하는 레코드만 생성/연결하고 Claim은 DRAFT로 남긴다.
   REVIEW_REQUIRED/HARD_CONFLICT는 그대로 보존한다. 자동 생성 인원수를 미리 약속하지 않는다.
5. 정확한 DRAFT 선택과 근거·공개 권한을 검토한 뒤 기존 publication gate를 통과시킨다.
   공개 가능한 레코드만 public API→People→Person→Claim/Evidence→Source로 읽힌다.

source·identity·publication은 다른 효과이며, 하나의 수집 성공으로 세 단계를 승인하거나 완료하지 않는다.
추가 수집은 첫 사이트 데이터 경로를 검증한 후 기존 L3의 NEC 당선자 또는 ALIO item4 중
정확한 범위·정책·키·한도를 확정한 한 소스부터 진행한다. OpenDART는 review-only identity 경계를 유지한다.
CleanEye, 국회 재산 공개, 국감 위원회 HTML 등 blocked/route-rights 미해결 소스는 이 단계에서 실행하지 않는다.

재요청을 원하지 않으면 국회 전용 canonical transfer를 별도 변경으로 검토할 수 있다.
그 경로는 아직 구현되지 않았고, source/snapshot/policy/run/checkpoint/observation의 출처·ID 보존과
cross-DB 충돌·idempotency 검증이 필요하다. 범용 importer/새 ETL 프레임워크를 먼저 만들지 않는다.

## 역할과 협업 방식

이번 상태 점검은 배포, 데이터, 프론트엔드의 세 독립 서브에이전트가 수행했고 MAIN이 주요 결과를 재확인했다.
앞으로도 MAIN 한 명과 최대3개 동시 작업 슬롯을 사용한다. 하위 에이전트의 재위임은 하지 않는다.

| 담당 | 맡길 작업 | 접근/쓰기 경계 | 반환할 증거 |
|---|---|---|---|
| Codex MAIN | 출시 기준, 공통 계약, API/domain/identity/DB, 통합과 최종 실행 | 공유 파일과 운영 writer의 단일 소유자 | 통합 커밋·검증·실행 receipt |
| Claude Opus | Person→Claim→Evidence→Source 읽기 흐름, 한국어 문구, 모바일 근거 표시 | 승인한 프론트 코드와 합성 fixture. 실제 DB·키·배포 도구 없음 | 파일별 patch, 디자인 근거, 변경 경로 |
| source_worker / curator | 정확한 source 범위, 관측/identity 충돌과 coverage 분석, 수집 요청 준비 | source 연구와 격리된 fixture. 운영 쓰기는 MAIN | 정책·scope·target·예산·예외 목록 |
| 배포 준비 담당 | 기존 topology, 기준 커밋, CI·backup·migration·rollback 준비 | 초기에는 읽기 전용. MAIN이 배포 수행 | read-only plan 및 smoke/복구 계획 |
| 독립 Quality / Risk | 실제 diff·회귀·출처·개인정보·외부 모델 문맥·공개 범위 검토 | 구현을 직접 수정하지 않음. 준비 슬롯이 끝난 뒤 배정 | 재현 가능한 finding 및 확인된 수용 결과 |

Opus를 Codex의 다른 모델 에이전트인 것처럼 표시하지 않는다. 설치된 Claude Code CLI를 별도 호출한다.
기존 로그인과 공식 `--model opus` 경로를 사용하되, 실제 응답의 model usage로 실행 모델을 기록한다.
이번에는 로그인 상태만 조회했으며 추론 요청을 보내지 않았다.

첫 Opus 협업은 승인된 텍스트 코드 패킷을 전달하고 파일별 patch를 받는 방식으로 시작한다.
모델의 파일·shell·MCP 도구 없이 bounded UI 문맥만 제공하고, CLI의 custom hooks/plugins/MCP 상속을
제한한 구성을 먼저 확인한다. source key·deployment 환경·private 레코드는 전달하지 않는다.
MAIN이 patch 적용 경로와 base를 검증하고 격리 worktree에 적용한 뒤 테스트한다.
직접 편집 권한을 주는 방식은 실제 도구·파일 접근 경계를 검증한 별도 작업 주문에서만 사용한다.
worktree와 프롬프트 자체를 credential isolation 증명으로 표현하지 않는다.

대표 화면은 기존 `apps/web/app/people/[id]/page.tsx`다. 이전 Home/People 개선은 Person dossier
구조를 제외했으므로, 섹션 탐색·근거 행·출처 disclosure를 먼저 일관되게 개선한다.
새 공개 데이터가 준비되기 전에는 명시된 합성/회귀 fixture로 검증하며 실제 국회 공개 coverage로 표현하지 않는다.

`DESIGN.md`는 MAIN이 통합하고, `data.ts`, `types.ts`, API/domain 계약, lockfile, migration,
root instruction과 HANDOFF는 MAIN 소유다. `styles.css`, 공유 layout/components, UI test 파일은
작업마다 단일 소유자를 정한다. 다른 슬롯과 동시에 같은 공통 파일을 수정하지 않는다.
Opus는 필요한 공통 변경을 제안으로 반환한다. 대체 데모·새 디자인 시스템·새 의존성부터 만들지 않는다.

## 실행 순서와 수용 기준

| 단계 | 병행 가능한 작업 | 다음 단계 조건 |
|---|---|---|
| 0. 기준 고정 | MAIN release base 확정; source target preflight; Opus 최소 문맥 준비 | 원본 사용자 변경 보존, 소유 경로·DB·port·효과/예산 명시 |
| 1. 대표 UI와 데이터 준비 | Opus dossier patch; source 정책/관측 검토; CI/배포·복구 준비 | API DTO와 공개 상태 계약 합의, 정확한 작업 요청 |
| 2. 통합 검증 | MAIN patch 통합; Quality/Risk가 독립 검토 | 관련 check 및 `make verify`, 필요한 PostgreSQL 실행 증거 |
| 3. 데이터 실행 | MAIN만 승인된 대상에서 수집→감사→materialize→별도 공개 | source/coverage/identity/publication 각각의 receipt와 post-read |
| 4. staging 검증 | 고정 커밋의 artifact·migration·API/public read·Web smoke | 배포 SHA와 CI 일치, backup/restore, 실제 Aside UI 수용 |
| 5. 운영 출시 | 구체적 production read-only plan 및 데이터 배치 계획 | 비용·서비스·공개 Web·indexing 선택 확정 후 승인 범위만 적용 |

도메인 계약의 의미가 바뀌면 MAIN이 먼저 결정하고 소비자인 Opus에 확정 DTO를 전달한다.
단순 UI 개선과 데이터/배포 준비는 병행하지만 운영 DB write·migration·publication은 직렬 실행한다.
할당표/advisory lock을 universal shared-writer lease로 부르지 않는다.
강제 중단, 403/429, rights 불명확, coverage 미완료, source version drift는 해당 단계의 명시적 중단이다.

UI는 lint/typecheck/tests/build/standalone을 통과한 뒤 Aside로 실제 데스크톱과 좁은 화면을 확인한다.
디렉터리→상세→섹션→근거→출처 이동, keyboard focus, 한국어 긴 문구, empty/error/not-found,
UNKNOWN/PARTIAL/conflict와 overflow를 검증한다. 실제 캡처를 직접 열어 확인한다.
현재 Aside 데몬 부재로 이 수용 검증은 미완료다. 준비가 복구된 후 공식 REPL/API probe부터 재확인한다.
다른 브라우저로 우회하지 않는다.

새 production 서비스, 유료 플랜 변경, 공개 범위 확대 및 indexing은 이번 계획으로 실행하지 않는다.
선택한 범위의 구현·테스트·검토는 이어서 수행하고, 외부 적용에 필요한 최종 검토는 정확한 변경·비용·
데이터/공개 선택을 담은 구체적인 결과에서 한다. 소요 기간이나 비용은 아직 측정하지 않았다.

## 선택지

| 선택 | 우선 진행 | 처음 확인할 결과 | 장단점 |
|---|---|---|---|
| 1. 국회 파일럿 통합 — 추천 | Opus dossier 개선 + 사이트용 국회 target 준비를 병행하고 기존 staging에서 합친다 | 검토를 통과한 실제 레코드의 인물→근거→출처 읽기 흐름 | UI·데이터·배포를 한 흐름으로 검증. 대상 PG의 별도 수집/쓰기·공개 범위 확정 필요 |
| 2. 배포 기반 우선 | 현재 코드의 정확한 release/CI/backup 및 staging 검증부터 | 어느 커밋·schema·artifact가 서비스되는지 확인된 사이트 | 배포 불확실성을 먼저 줄임. 데이터와 화면 개선은 뒤에 진행 |
| 3. Opus 프론트엔드 우선 | 합성 fixture로 dossier의 한국어·모바일·근거 읽기 흐름부터 | 기존 canonical UI에 적용할 patch와 실제 화면 검증 | UI 작업 경계가 가장 작음. 데이터 연결과 배포 완료를 증명하지는 않음 |

1번을 권장한다. 국회 한 소스의 공개 가능한 파일럿을 먼저 끝낸 뒤 추가 소스를 확장한다.
사용자 선택은 1번이다. 작업 범위와 진행 증거는 연결된 active ExecPlan에 기록한다.

## 근거와 실제 점검

- [완료 수집/감사 receipt](../receipts/mac-collector-bounded-20261002.md),
  [canonical audit JSON](../receipts/assembly-one-shot-live-audit-20261002.json).
- [CLI 효과 및 기존 경로](COMMANDS.md), [배포·데이터 loading 경계](EVIDENCE_PREVIEW_DEPLOYMENT.md),
  [역할·공유 자원](../roles/ROLE_MODEL.md), [디자인 계약](../../DESIGN.md),
  [source coverage](../architecture/FEEDER_SOURCE_COVERAGE.md).
- Railway connector의 projects/services/status/config/domains/deployments 조회와 `gh run list`.
  MAIN이 staging/production status를 재조회하고 기존 Web 루트 GET200을 확인했다.
- Mac은 Remote Desktop Commander에서 SQLite `mode=ro`로 상태/count/schema를 재확인했다.
  키 내용·source row 값은 보고서에 포함하지 않았다.
- 로컬 `git status`, `git log`, `git rev-list`, Claude `--version`/`--help`/`auth status`를 조회했다.
- Aside `guide`, `guide repl`, `--version`, `account list`를 실행했다.
  account 조회 실패 후 비파괴 process/listener 진단에서 `DAEMON_PROCESS_MISSING`을 확인했다.
  브라우저 fallback, 설정/권한 변경, 설치, 계정 변경, 새 Claude 추론, 배포, 데이터 mutation은 하지 않았다.
- Claude CLI의 모델 선택/비대화형 협업 경로는
  [공식 model 문서](https://code.claude.com/docs/en/model-config)와
  [공식 CLI 문서](https://code.claude.com/docs/en/cli-reference)를 확인했다.
