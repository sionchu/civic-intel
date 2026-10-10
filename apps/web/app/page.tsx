import Link from "next/link";

import ReadState from "./components/read-state";
import { getGukgamTargets, getPeople } from "./data";
import { AuditBrief } from "./components/kst-schedule";
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
  const renderedToday = process.env.CIVIC_SITES_EXPORT === "1" ? null : today;
  const scheduleGroups = targetsResult.state === "success"
    ? groupByDateAndCommittee(targetsResult.data.items, today)
    : [];
  const scheduleDays = scheduleGroups.map((group) => ({
    date: group.date,
    count: group.count,
    committeeCount: group.committees.length,
    // The first three records in the canonical committee/time/institution order.
    rows: group.committees.flatMap((committee) => committee.items.map((item) => ({
      claimId: item.claim_id,
      organizationId: item.organization.id,
      organization: item.organization.name,
      committee: committee.committee,
      time: item.time_text,
      sourcePublishedDate: item.source_published_date,
      pageNumber: item.page_number,
    }))).slice(0, 3),
  }));

  return (
    <div className="site-page home-page">
      <section className="home-intro home-search" aria-labelledby="hero-title">
        <h1 id="hero-title">모두의국감 <span lang="ko">공적 기록 탐색</span></h1>
        <p className="lede">인물과 기관의 공적 이력, 활동과 연결을 공개 기록에서 살펴봅니다.</p>
        <form className="home-search-form" action="/people" method="get" role="search">
          <label className="gukgam-search-field">
            <span className="sr-only">인물 이름으로 검색</span>
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              type="search"
              name="q"
              placeholder="인물 이름으로 공개 기록 찾기"
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
          <h2 id="home-today-title">국감 브리프 <span className="domain-label" lang="ko">국감 일정</span></h2>
          {targetsResult.state === "error" ? (
            <ReadState error={targetsResult.error} />
          ) : (
            <AuditBrief serverToday={renderedToday} days={scheduleDays} />
          )}
          <p><Link href="/gukgam/2026">전체 감사 일정과 위원회 보기</Link></p>
        </section>

        <section className="home-block" aria-labelledby="home-explore-title">
          <h2 id="home-explore-title">공개 기록 탐색 <span className="domain-label" lang="ko">탐색</span></h2>
          <nav aria-label="공개 기록 탐색">
            <ul className="home-explore-list">
              <li><Link href="/people">인물</Link><span>공적 경력 · 입법 · 표결 · 출처</span></li>
              <li><Link href="/organizations">기관·기업</Link><span>공식 직책 · 국감 계획 · 공개 공시</span></li>
              <li><Link href="/people#filter-party">정당별 인물</Link><span>공개된 국회 소속 기록으로 찾기</span></li>
              <li><Link href="/people#filter-committees">위원회별 인물</Link><span>각 소속 위원회로 좁혀 보기</span></li>
              <li><Link href="/gukgam/2026">국정감사 2026</Link><span>계획 일정 · 대상 기관 · 출석 요구 명단</span></li>
              <li><Link href="/market">지역별 거래 동향</Link><span>행정경계 탐색 · 공식 거래통계 연결 현황</span></li>
            </ul>
          </nav>
        </section>
      </div>

      <section className="principles" id="coverage" aria-labelledby="principles-title">
        <h2 id="principles-title">자료 범위</h2>
        <p className="principles-lede">공개 조건을 충족한 기록을 출처별로 제공합니다. 전체 인물 이력이나 국감 참여자·증인 명단을 포괄하지 않습니다.</p>
        {peopleCount !== null && (
          <p className="coverage-note">공개 인물 {peopleCount.toLocaleString("ko-KR")}명{latestAsOf ? ` · 국회 기본정보의 가장 최근 자료 기준일 ${latestAsOf}` : ""}</p>
        )}
      </section>
    </div>
  );
}
