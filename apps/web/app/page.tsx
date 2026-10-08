import Link from "next/link";

import ReadState from "./components/read-state";
import { getGukgamTargets, getPeople } from "./data";
import { AuditBrief } from "./components/kst-schedule";
import { groupByDateAndCommittee, renderedKstToday, seoulDate } from "./gukgam/2026/schedule";

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

  const now = new Date();
  const today = renderedKstToday(now);
  const scheduleGroups = targetsResult.state === "success"
    ? groupByDateAndCommittee(targetsResult.data.items, seoulDate(now))
    : [];
  // Each day keeps the canonical schedule order (committee, time, institution); the brief shows
  // only the first three rows of that order plus the remaining count, never a selection.
  const scheduleDays = scheduleGroups.map((group) => ({
    date: group.date,
    count: group.count,
    committeeCount: group.committees.length,
    rows: group.committees
      .flatMap((committee) => committee.items.map((item) => ({
        claimId: item.claim_id,
        committee: committee.committee,
        organization: item.organization.name,
        time: item.time_text,
      })))
      .slice(0, 3),
  }));

  return (
    <div className="site-page home-page">
      <section className="home-intro home-search" aria-labelledby="hero-title">
        <h1 id="hero-title">국정감사 인물 기록 검색</h1>
        <p className="lede">국회의원과 2026 국정감사 관련 인물의 공개 기록을 찾습니다.</p>
        <form className="home-search-form" action="/people" method="get" role="search">
          <label className="gukgam-search-field">
            <span className="sr-only">인물 이름으로 검색</span>
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              type="search"
              name="q"
              placeholder="인물 이름 (예: 안철수)"
              autoComplete="off"
              maxLength={80}
              required
            />
          </label>
          <button className="primary-action" type="submit">검색</button>
        </form>
      </section>

      {peopleResult.state === "error" && <div className="home-read-state"><ReadState error={peopleResult.error} /></div>}

      <div className="home-columns">
        <section className="home-block" aria-labelledby="home-today-title">
          <h2 id="home-today-title">국감 일정</h2>
          {targetsResult.state === "error" ? (
            <p className="coverage-caption">국감 일정을 불러오지 못했습니다.</p>
          ) : (
            <AuditBrief serverToday={today} days={scheduleDays} />
          )}
          <p><Link href="/gukgam/2026">전체 일정 보기</Link></p>
        </section>

        <section className="home-block" aria-labelledby="home-people-title">
          <h2 id="home-people-title">인물 기록</h2>
          <p className="home-block-meta">
            {peopleCount === null
              ? "인물 기록 수를 불러오지 못했습니다."
              : `공개 ${peopleCount}명${latestAsOf ? ` · 최신 출처 기준일 ${latestAsOf}` : ""}`}
          </p>
          <p><Link href="/people">인물 찾기</Link></p>
        </section>
      </div>

      <section className="principles" id="coverage" aria-labelledby="principles-title">
        <h2 id="principles-title">자료 범위</h2>
        <p className="principles-lede">공식 기록으로 확인된 내용만 싣습니다. 모든 국감 참여자나 전체 증인 명단은 아닙니다.</p>
      </section>
    </div>
  );
}
