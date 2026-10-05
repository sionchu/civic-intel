import Link from "next/link";

import ReadState from "./components/read-state";
import { getGukgamTargets, getOrganizations, getPeople } from "./data";
import type { ApiResult } from "./types";
import { focusDate, formatAuditDate, groupByDateAndCommittee, seoulDate } from "./gukgam/2026/schedule";

export const dynamic = "force-dynamic";

function count(result: ApiResult<unknown[]>): string {
  return result.state === "success" ? `${result.data.length}건` : "불러오지 못함";
}

export default async function HomePage() {
  const [peopleResult, organizationsResult, targetsResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
    getGukgamTargets(),
  ]);
  const today = seoulDate(new Date());
  const scheduleGroups = targetsResult.state === "success" ? groupByDateAndCommittee(targetsResult.data.items, today) : [];
  const nextDate = focusDate(scheduleGroups);
  const nextGroup = scheduleGroups.find((group) => group.date === nextDate) ?? null;

  return (
    <div className="site-page home-page">
      <section className="home-intro" aria-labelledby="hero-title">
        <p className="eyebrow">Civic Intel / 공개 기록 디렉터리</p>
        <h1 id="hero-title">공개 기록을 근거와 함께 읽는 디렉터리</h1>
        <p className="lede">
          사람과 기관에 대해 공개된 기록만 보여주고, 모든 항목에서 Claim · Evidence · 출처와 기준일로 이어집니다.
          평가나 점수를 매기지 않으며, 근거가 없는 항목은 UNKNOWN으로 남겨 둡니다.
        </p>
        <p className="home-path" aria-label="읽는 순서">
          <span>Identity</span><span aria-hidden="true">→</span>
          <span>공개 기록</span><span aria-hidden="true">→</span>
          <span>Claim</span><span aria-hidden="true">→</span>
          <span>Evidence</span><span aria-hidden="true">→</span>
          <span>Source</span>
        </p>
      </section>

      <section className="home-gukgam" aria-labelledby="gukgam-invite-title">
        <div className="home-section-heading">
          <h2 id="gukgam-invite-title">국감 2026</h2>
          <Link className="inline-action" href="/gukgam/2026">전체 감사 일정 <span aria-hidden="true">↗</span></Link>
        </div>
        {targetsResult.state === "error" ? (
          <ReadState error={targetsResult.error} />
        ) : nextGroup ? (
          <div className="home-gukgam-next">
            <p className="home-gukgam-date">
              <span>{nextGroup.relation === "today" ? "오늘" : "다음 감사일"}</span>
              <Link href={`/gukgam/2026#audit-${nextGroup.date}`}>{formatAuditDate(nextGroup.date)}</Link>
            </p>
            <ul className="home-gukgam-committees">
              {nextGroup.committees.map((committee) => (
                <li key={committee.committee}>
                  <strong>{committee.committee}</strong>
                  <span>
                    {committee.items.map((item, index) => (
                      <span key={item.claim_id}>
                        {index > 0 && " · "}
                        <Link href={`/organizations/${item.organization.id}`}>{item.organization.name}</Link>
                      </span>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
            <p className="home-note">
              위원회 공식 계획서상 일정(계획 사실)이며, 공개 기준을 통과한 위원회·기관만 포함합니다. 전체 감사대상 목록이 아닙니다.
            </p>
          </div>
        ) : (
          <p className="home-note"><span className="status UNKNOWN">UNKNOWN</span> 앞으로 남은 공개 감사 일정이 없습니다.</p>
        )}
      </section>

      <section className="home-directory" aria-labelledby="directory-invite-title">
        <div className="home-section-heading">
          <h2 id="directory-invite-title">기록 찾기</h2>
        </div>
        <ul className="home-directory-list">
          <li>
            <Link href="/people">사람 기록 탐색</Link>
            <span>이름과 공개 기록의 정당·지역구·위원회·선수로 찾기</span>
            <small>공개 기록 {count(peopleResult)}</small>
          </li>
          <li>
            <Link href="/organizations">기관 기록 탐색</Link>
            <span>공공기관 분류, 임원 공시, 국정감사 피감 일정</span>
            <small>공개 기록 {count(organizationsResult)}</small>
          </li>
          <li>
            <Link href="/gukgam/2026">국감 2026</Link>
            <span>날짜 → 위원회 → 피감기관 → 위원 → 근거</span>
            <small>{targetsResult.state === "success" ? `공개 일정 ${targetsResult.data.target_count}건` : "불러오지 못함"}</small>
          </li>
        </ul>
        {peopleResult.state === "error" && <div className="home-read-state"><ReadState error={peopleResult.error} /></div>}
      </section>
    </div>
  );
}
