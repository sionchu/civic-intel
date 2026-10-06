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

  const featuredPeople = peopleResult.state === "success" ? peopleResult.data.slice(0, 8) : [];

  return (
    <div className="site-page home-page">
      <section className="home-intro home-search" aria-labelledby="hero-title">
        <h1 id="hero-title">국정감사 인물 기록 검색</h1>
        <p className="lede">국회의원과 2026 국정감사 관련 인물의 공개 기록을 출처와 함께 찾습니다.</p>
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
        <p className="home-trust-note">동명이인과 미확인 관계는 자동으로 합치지 않습니다.</p>
      </section>

      {peopleResult.state === "error" && <div className="home-read-state"><ReadState error={peopleResult.error} /></div>}

      <div className="home-columns">
        <section className="home-block" aria-labelledby="home-today-title">
          <h2 id="home-today-title">오늘 국감 일정</h2>
          <p className="home-block-meta"><KstToday serverToday={today} /></p>
          {targetsResult.state === "error" ? (
            <p className="coverage-caption">국감 일정을 불러오지 못했습니다.</p>
          ) : (
            <TodayAuditLine serverToday={today} days={scheduleDays} />
          )}
          <p><Link href="/gukgam/2026">전체 감사 일정과 위원회 보기</Link></p>
        </section>

        <section className="home-block" aria-labelledby="home-people-title">
          <h2 id="home-people-title">인물 기록</h2>
          <p className="home-block-meta">
            {peopleCount === null
              ? "인물 기록 수를 불러오지 못했습니다."
              : `공개 ${peopleCount}명${latestAsOf ? ` · 최신 출처 기준일 ${latestAsOf}` : ""}`}
          </p>
          {featuredPeople.length > 0 && (
            <ul className="home-people-list">
              {featuredPeople.map((person) => {
                const facets = person.discovery?.facets;
                const detail = [facets?.role?.value, facets?.party?.value].filter(Boolean).join(" · ");
                return (
                  <li key={person.id}>
                    <Link href={`/people/${person.id}`}>{person.canonical_name}</Link>
                    {detail && <span>{detail}</span>}
                  </li>
                );
              })}
            </ul>
          )}
          <p><Link href="/people">전체 인물 목록 보기</Link></p>
        </section>
      </div>

      <section className="principles" id="coverage" aria-labelledby="principles-title">
        <h2 id="principles-title">자료 범위</h2>
        <p className="principles-lede">
          모든 국감 참여자나 전체 증인 명단이 아닙니다. 여기에 없는 사람이나 관계는 없다는 뜻이 아니라 아직 확인되지
          않았다는 뜻입니다.
        </p>
        <dl className="principles-list">
          <div><dt>인물 구분</dt><dd>이름이 같다는 이유만으로 기록을 합치지 않습니다.</dd></div>
          <div><dt>근거</dt><dd>표시된 내용마다 근거를 열어 볼 수 있고, 확인되지 않은 값은 비워 둡니다.</dd></div>
          <div><dt>출처와 기준일</dt><dd>공식 출처와 기준일을 함께 표시합니다.</dd></div>
          <div><dt>평가하지 않음</dt><dd>정치 성향, 점수, 순위를 만들지 않습니다. 증인·참고인 명단의 이름은 인물 기록에 자동으로 연결하지 않습니다.</dd></div>
        </dl>
      </section>
    </div>
  );
}
