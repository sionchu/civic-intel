import type { Metadata } from "next";
import Link from "next/link";

import GukgamSearch, { type GukgamSearchFacets } from "../../components/gukgam-search";
import type { Person } from "../../types";
import CommitteeMembers from "../../components/committee-members";
import GukgamWitnesses from "../../components/gukgam-witnesses";
import { AuditDateIndex, AuditDaySection, KstToday, NextAuditAction } from "../../components/kst-schedule";
import ReadState from "../../components/read-state";
import { getGukgamCommittees, getGukgamTargets, getOrganizations, getPeople } from "../../data";
import { buildPageMetadata } from "../../site-metadata";
import { committeeAnchor } from "./committees";
import { groupByDateAndCommittee, seoulDate } from "./schedule";

export const dynamic = "force-dynamic";

type FacetSource = NonNullable<Person["discovery"]>["facets"];

function facetValue(facet: { value: string } | null): { value: string } | null {
  return facet ? { value: facet.value } : null;
}

function searchFacets(facets: FacetSource): GukgamSearchFacets {
  return {
    role: facetValue(facets.role),
    party: facetValue(facets.party),
    district: facetValue(facets.district),
    committees: facetValue(facets.committees),
    reelection: facetValue(facets.reelection),
  };
}

export const metadata = buildPageMetadata({
  title: "국감 2026",
  description: "2026 국정감사 일정·피감기관·감사 위원을 공식 기록과 근거로 확인하는 모두의국감 화면",
  path: "/gukgam/2026",
});

export default async function Gukgam2026Page({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[] }>;
}) {
  const params = await searchParams;
  const initialQuery = typeof params.q === "string" ? params.q.slice(0, 80) : "";

  const [peopleResult, organizationsResult, targetsResult, committeesResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
    getGukgamTargets(),
    getGukgamCommittees(),
  ]);

  const peopleCount = peopleResult.state === "success" ? peopleResult.data.length : null;
  const organizationCount = organizationsResult.state === "success" ? organizationsResult.data.length : null;

  const committees = committeesResult.state === "success" ? committeesResult.data.committees : [];
  const committeeByName = new Map(committees.map((committee) => [committee.committee_name, committee]));
  const today = seoulDate(new Date());
  const targetItems = targetsResult.state === "success" ? targetsResult.data.items : [];
  const scheduleGroups = groupByDateAndCommittee(targetItems, today);
  const scheduleDays = scheduleGroups.map((group) => ({
    date: group.date,
    count: group.count,
    committeeCount: group.committees.length,
  }));
  const scheduleDates = scheduleDays.map((day) => day.date);
  const coveredCommittees = [...new Set(targetItems.map((item) => item.committee_name))].sort(
    (left, right) => left.localeCompare(right, "ko"),
  );
  const planDates = [...new Set(targetItems.map((item) => item.source_published_date))].sort();
  const planDateRange = planDates.length === 0
    ? null
    : planDates.length === 1 ? planDates[0] : `${planDates[0]} ~ ${planDates[planDates.length - 1]}`;

  return (
    <div className="site-page gukgam-page">
      <header className="gukgam-hero">
        <div className="gukgam-hero-copy">
          <h1>국감 2026</h1>
          <p className="lede">
            2026 국정감사 일정, 피감기관, 위원회 위원, 증인·참고인 명단입니다.
          </p>
          <div className="hero-actions">
            <NextAuditAction serverToday={today} dates={scheduleDates} />
            <a className="inline-action" href="#gukgam-witnesses-title">증인·참고인 명단</a>
            <Link className="inline-action" href="/people">인물 찾기</Link>
            <Link className="inline-action" href="/organizations">기관 보기</Link>
          </div>
        </div>
      </header>

      <section className="gukgam-entry-section" aria-labelledby="gukgam-published-targets-title">
        <div className="section-intro">
          <h2 id="gukgam-published-targets-title">감사일별 공개된 피감대상</h2>
        </div>

        {targetsResult.state === "error" ? (
          <ReadState error={targetsResult.error} />
        ) : targetsResult.data.items.length === 0 ? (
          <div className="empty-state" role="status">
            <div>
              <strong>아직 공개된 피감대상이 없습니다.</strong>
            </div>
          </div>
        ) : (
          <>
            <dl className="gukgam-scope" aria-label="공개 일정의 범위와 기준 시점">
              <div>
                <dt>공개 범위</dt>
                <dd>{targetsResult.data.target_count}건 · {coveredCommittees.length}개 위원회</dd>
              </div>
              <div>
                <dt>포함 위원회</dt>
                <dd>{coveredCommittees.join(" · ")}</dd>
              </div>
              <div>
                <dt>근거 계획서 공개일</dt>
                <dd>{planDateRange ?? "—"}</dd>
              </div>
              <div>
                <dt>오늘 (KST)</dt>
                <dd><KstToday serverToday={today} /></dd>
              </div>
            </dl>
            <p className="gukgam-scope-note">
              전체 감사대상 목록이 아닙니다. 위원회 계획서상 일정이며 바뀔 수 있습니다.
            </p>

            <AuditDateIndex serverToday={today} days={scheduleDays} />

            <div className="gukgam-schedule" id="gukgam-schedule">
              {scheduleGroups.map((group) => (
                <AuditDaySection
                  key={group.date}
                  serverToday={today}
                  date={group.date}
                  dates={scheduleDates}
                  count={group.count}
                >
                  {group.committees.map((committee) => (
                    <div className="gukgam-committee" key={committee.committee}>
                      <h4>{committee.committee}</h4>
                      <ul className="gukgam-target-rows">
                        {committee.items.map((item) => (
                          <li className="gukgam-target-row" key={item.claim_id}>
                            <div className="gukgam-target-main">
                              <Link href={`/organizations/${item.organization.id}`}>
                                {item.organization.name}
                              </Link>
                              <p>
                                {item.time_text ?? "시간 미기재"}
                                {item.venue ? ` · ${item.venue}` : ""}
                              </p>
                            </div>
                            <div className="gukgam-target-evidence">
                              <span className="status FACT" title="공식 계획서상 피감대상이라는 계획 사실">FACT</span>
                              <small>
                                공식 계획서 {item.source_published_date} 공개 · {item.section} · p.{item.page_number}
                              </small>
                              <Link
                                className="inline-action"
                                href={`/organizations/${item.organization.id}#claim-${item.claim_id}`}
                              >
                                이 일정의 근거 보기
                              </Link>
                              <details className="audit-details">
                                <summary>Claim·Evidence 확인 경로</summary>
                                <small>
                                  Claim {item.claim_id}<br />
                                  Evidence {item.evidence_ids.join(", ")}<br />
                                  Source {item.source_ids.join(", ")}<br />
                                  SourceSnapshot {item.snapshot_ids.join(", ")}<br />
                                  FeederObservation {item.observation_ids.join(", ")}
                                </small>
                              </details>
                            </div>
                          </li>
                        ))}
                      </ul>
                      {committeeByName.has(committee.committee) && (
                        <Link className="gukgam-committee-members-link" href={`#${committeeAnchor(committee.committee)}`}>
                          감사 위원 {committeeByName.get(committee.committee)!.member_count}명 <span aria-hidden="true">→</span>
                        </Link>
                      )}
                    </div>
                  ))}
                </AuditDaySection>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="gukgam-entry-section" id="gukgam-committees" aria-labelledby="gukgam-committees-title">
        <div className="section-intro">
          <h2 id="gukgam-committees-title">위원회별 감사 위원</h2>
        </div>
        {committeesResult.state === "error" ? (
          <ReadState error={committeesResult.error} />
        ) : committees.length === 0 ? (
          <div className="empty-state" role="status">
            <div>
              <strong>아직 공개된 위원회 구성 기록이 없습니다.</strong>
            </div>
          </div>
        ) : (
          <>
            <p className="gukgam-scope-note">
              국회 명부 기준 위원입니다.
            </p>
            <ul className="committee-index">
              {committees.map((committee) => (
                <li key={committee.committee_name} id={committeeAnchor(committee.committee_name)}>
                  <div className="committee-index-heading">
                    <h3>{committee.committee_name}</h3>
                    <span>
                      {committee.target_claim_coverage === "PUBLISHED"
                        ? `피감대상 ${committee.target_count}건`
                        : "피감대상 미공개"}
                      {" · "}위원 {committee.member_count}명
                    </span>
                  </div>
                  {committee.target_claim_coverage === "NOT_YET_PUBLISHED" && (
                    <p className="committee-targets-pending" role="note">
                      피감대상 공개 기록 준비 중 — 위원 명단만 표시
                    </p>
                  )}
                  <CommitteeMembers committee={committee} label="위원 명단" />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <GukgamWitnesses />

      <p className="gukgam-coverage-line">
        현재 공개 기록: 인물 {peopleCount === null ? "—" : `${peopleCount}명`} · 기관 {organizationCount === null ? "—" : `${organizationCount}곳`}
      </p>

      {peopleResult.state === "error" && <ReadState error={peopleResult.error} />}
      {organizationsResult.state === "error" && <ReadState error={organizationsResult.error} />}

      <GukgamSearch
        initialQuery={initialQuery}
        people={
          peopleResult.state === "success"
            ? peopleResult.data.map(({ id, canonical_name, discovery }) => ({
                id,
                canonical_name,
                discovery: discovery ? { facets: searchFacets(discovery.facets) } : undefined,
              }))
            : []
        }
        organizations={
          organizationsResult.state === "success" ? organizationsResult.data : []
        }
      />
    </div>
  );
}
