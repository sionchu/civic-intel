import Link from "next/link";

import ReadState from "./components/read-state";
import { getGukgamTargets, getPeople } from "./data";
import { KstToday, TodayAuditLine } from "./components/kst-schedule";
import { groupByDateAndCommittee, seoulDate } from "./gukgam/2026/schedule";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [peopleResult, targetsResult] = await Promise.all([getPeople(), getGukgamTargets()]);
  const peopleCount = peopleResult.state === "success" ? peopleResult.data.length : null;
  // Latest source as-of date among public discovery records; a display of existing values only.
  const latestAsOf = peopleResult.state === "success"
    ? peopleResult.data
        .map((person) => person.discovery?.as_of)
        .filter((value): value is string => Boolean(value))
        .sort()
        .at(-1) ?? null
    : null;

  const today = seoulDate(new Date());
  const scheduleGroups = targetsResult.state === "success"
    ? groupByDateAndCommittee(targetsResult.data.items, today)
    : [];
  const scheduleDays = scheduleGroups.map((group) => ({
    date: group.date,
    count: group.count,
    committeeCount: group.committees.length,
  }));

  return (
    <div className="site-page home-page">
      <section className="home-intro home-search" aria-labelledby="hero-title">
        <div className="home-intro-copy">
          <p className="eyebrow">모두의국감 · 2026 국정감사</p>
          <h1 id="hero-title">국감 참여 인물의<br />이력과 근거를 확인하세요</h1>
          <p className="lede">
            국회의원 등 공개 근거로 확인된 인물을 이름으로 찾고, 역할·이력과 2026 국정감사 관련
            맥락을 출처와 함께 확인할 수 있습니다.
          </p>
          <form className="home-search-form" action="/people" method="get" role="search">
            <label className="gukgam-search-field">
              <span className="sr-only">인물 이름으로 검색</span>
              <span className="search-icon" aria-hidden="true">⌕</span>
              <input
                type="search"
                name="q"
                placeholder="인물 이름으로 검색 (예: 안철수)"
                autoComplete="off"
                maxLength={80}
                required
              />
            </label>
            <button className="primary-action" type="submit">검색 <span aria-hidden="true">↗</span></button>
          </form>
          <p className="home-trust-note">
            확인 가능한 공개 기록만 보여줍니다. 동명이인과 미확인 관계는 자동으로 합치지 않습니다.
            {" "}<Link href="/people">전체 인물 목록 보기</Link>
          </p>
        </div>
        <aside className="home-coverage" aria-label="오늘의 국감 일정과 공개 범위">
          <div className="home-coverage-heading">
            <span className="micro-label">오늘 (KST)</span>
            <span className="coverage-index"><KstToday serverToday={today} /></span>
          </div>
          {targetsResult.state === "error" ? (
            <p className="coverage-caption">국감 일정을 불러오지 못했습니다.</p>
          ) : (
            <TodayAuditLine serverToday={today} days={scheduleDays} />
          )}
          <p className="coverage-note">
            {peopleCount === null
              ? "공개 인물 기록 수를 불러오지 못했습니다."
              : `현재 공개 인물 기록 ${peopleCount}명${latestAsOf ? ` · 최신 출처 기준일 ${latestAsOf}` : ""}`}
          </p>
        </aside>
      </section>

      {peopleResult.state === "error" && <div className="home-read-state"><ReadState error={peopleResult.error} /></div>}

      <section className="event-invite" aria-labelledby="gukgam-invite-title">
        <div className="event-invite-copy">
          <span className="eyebrow">2026 국정감사</span>
          <h2 id="gukgam-invite-title">국감 일정과 감사 위원</h2>
          <p>위원회 공식 계획서에서 확인된 감사일·피감기관과, 국회 명부에 기재된 위원회별 위원을 근거와 함께 봅니다.</p>
        </div>
        <div className="event-invite-meta">
          <span className="micro-label">공식 기록 기준</span>
          <p>계획서·피감기관·증인·참고인 자료는 출처 정책과 검토를 통과한 공식 기록만 순차 반영합니다.</p>
          <Link className="inline-action" href="/gukgam/2026">국감 일정 보기 <span aria-hidden="true">↗</span></Link>
        </div>
      </section>

      <section className="principles" id="coverage" aria-labelledby="principles-title">
        <div className="principles-heading">
          <span className="eyebrow">자료 범위</span>
          <h2 id="principles-title">확인 가능한 범위만<br />근거와 함께</h2>
          <p>
            모든 국감 참여자나 전체 증인 명단이 아닙니다. 공개 기준을 통과한 기록만 표시하며, 표시되지 않은
            사람·관계는 없다는 뜻이 아니라 아직 확인되지 않았다는 뜻입니다.
          </p>
        </div>
        <ol className="principles-list">
          <li className="principle"><div><strong>인물 구분</strong><p>공개 기록이 가리키는 사람을 먼저 구분합니다. 이름이 같다는 이유만으로 기록을 합치지 않습니다.</p></div></li>
          <li className="principle"><div><strong>근거</strong><p>표시된 내용마다 근거(Claim·Evidence)를 열어 볼 수 있고, 확인되지 않은 값은 비워 둡니다.</p></div></li>
          <li className="principle"><div><strong>출처와 기준일</strong><p>근거가 연결된 공식 출처와 기준일을 따라 원문과 기록의 범위를 확인합니다.</p></div></li>
          <li className="principle"><div><strong>평가하지 않음</strong><p>정치 성향, 점수, 순위, 평가를 만들지 않습니다. 증인·참고인 명단의 이름은 인물 기록에 자동 연결하지 않습니다.</p></div></li>
        </ol>
      </section>
    </div>
  );
}
