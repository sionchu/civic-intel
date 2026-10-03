import type { Metadata } from "next";
import Link from "next/link";

import GukgamSearch, { type GukgamSearchFacets } from "../../components/gukgam-search";
import type { Person } from "../../types";
import CommitteeMembers from "../../components/committee-members";
import ReadState from "../../components/read-state";
import { getGukgamCommittees, getGukgamTargets, getOrganizations, getPeople } from "../../data";
import { buildPageMetadata } from "../../site-metadata";
import { committeeAnchor } from "./committees";
import { focusDate, formatAuditDate, groupByDateAndCommittee, seoulDate } from "./schedule";

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
  description: "2026 국정감사를 인물·기관·공식 기록과 Evidence를 통해 탐색하는 Civic Intel 이벤트 화면",
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
  const nextDate = focusDate(scheduleGroups);
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
          <p className="eyebrow">Civic Intel / Event surface</p>
          <h1>국감 <em>2026</em></h1>
          <p className="lede">
            국정감사에서 등장하는 인물과 기관을 기존 공개 기록과 공식 Evidence에 연결해 살펴봅니다.
            일정·피감기관·증인·참고인 정보는 출처 정책과 검증을 통과한 범위만 순차 반영합니다.
          </p>
          <div className="hero-actions">
            <a className="primary-action" href={nextDate ? `#audit-${nextDate}` : "#gukgam-published-targets-title"}>
              {nextDate === today ? "오늘 감사 일정 보기" : "감사 일정 보기"} <span aria-hidden="true">↓</span>
            </a>
            <Link className="inline-action" href="/people">인물 탐색 <span aria-hidden="true">↗</span></Link>
            <Link className="inline-action" href="/organizations">기관 탐색 <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
        <aside className="gukgam-method" aria-label="국감 화면의 공개 원칙">
          <span className="micro-label">Launch principle</span>
          <strong>공식 기록상 연결만</strong>
          <p>같은 이름, 같은 학교명 또는 단순한 동시 등장만으로 관계를 만들지 않습니다. 각 연결은 Claim과 Evidence를 따라 원문까지 확인할 수 있어야 합니다.</p>
        </aside>
      </header>

      <section className="gukgam-entry-section" aria-labelledby="gukgam-published-targets-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Audit schedule / Claim-backed</span>
            <h2 id="gukgam-published-targets-title">감사일별 공개된 피감대상</h2>
          </div>
          <p>
            위원회 공식 계획서의 피감대상 가운데 기관 기록에 검토 연결되고 Claim과 Evidence까지
            갖춘 일정만 날짜 → 위원회 → 기관 순으로 보여줍니다. 기관을 누르면 공개 기록과 근거로 이어집니다.
          </p>
        </div>

        {targetsResult.state === "error" ? (
          <ReadState error={targetsResult.error} />
        ) : targetsResult.data.items.length === 0 ? (
          <div className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <div>
              <strong>현재 공개된 피감대상 Claim이 없습니다.</strong>
              <p>
                감사대상이 없다는 뜻이 아니라, 현재 공개 기준을 통과한 Claim이 아직 없다는 뜻입니다.
              </p>
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
                <dd>{formatAuditDate(today)}</dd>
              </div>
            </dl>
            <p className="gukgam-scope-note">
              전체 감사대상 목록이 아닙니다. 위에 없는 위원회·기관은 아직 공개 기준을 통과하지 않았을 뿐이며,
              감사가 없다는 뜻이 아닙니다. 각 항목은 공식 계획서상 일정(계획 사실)이며 감사가 실제로
              열렸거나 어떤 결과가 나왔다는 기록이 아닙니다. 일정은 위원회 의결로 바뀔 수 있습니다.
            </p>

            <nav className="gukgam-date-index" aria-label="감사일별 이동">
              <ol>
                {scheduleGroups.map((group) => (
                  <li key={group.date} className={group.relation}>
                    <a
                      href={`#audit-${group.date}`}
                      aria-current={group.date === nextDate ? "date" : undefined}
                    >
                      <span>{formatAuditDate(group.date)}</span>
                      <small>
                        {group.relation === "today" ? "오늘 · " : group.date === nextDate ? "다음 · " : ""}
                        {group.count}건
                      </small>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>

            <div className="gukgam-schedule" id="gukgam-schedule">
              {scheduleGroups.map((group) => (
                <section
                  key={group.date}
                  id={`audit-${group.date}`}
                  className={`gukgam-day ${group.relation}`}
                  aria-labelledby={`audit-${group.date}-title`}
                >
                  <header className="gukgam-day-heading">
                    <h3 id={`audit-${group.date}-title`}>{formatAuditDate(group.date)}</h3>
                    <span>
                      {group.relation === "today"
                        ? "오늘 열리는 감사 일정"
                        : group.relation === "past"
                          ? "지난 일정 · 계획 기준"
                          : group.date === nextDate ? "다음 감사일" : "예정"}
                      {" · "}{group.count}건
                    </span>
                  </header>
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
                                이 일정의 Claim / Evidence 보기 <span aria-hidden="true">↗</span>
                              </Link>
                              <details className="audit-details">
                                <summary>Claim / Evidence audit trace</summary>
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
                </section>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="gukgam-entry-section" id="gukgam-committees" aria-labelledby="gukgam-committees-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Committee members / Claim-backed</span>
            <h2 id="gukgam-committees-title">위원회별 감사 위원</h2>
          </div>
          <p>
            공개된 피감대상 Claim이 있는 위원회마다, 국회 명부 Claim에 그 위원회가 기재된 현재 공개 의원을
            보여줍니다. 위원 이름은 인물 기록으로, 근거는 해당 Claim으로 이어집니다.
          </p>
        </div>
        {committeesResult.state === "error" ? (
          <ReadState error={committeesResult.error} />
        ) : committees.length === 0 ? (
          <div className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <div>
              <strong>공개된 위원회 구성 Claim이 없습니다.</strong>
              <p>위원이 없다는 뜻이 아니라, 현재 공개 기준을 통과한 Claim이 없다는 뜻입니다.</p>
            </div>
          </div>
        ) : (
          <>
            <p className="gukgam-scope-note">
              국회 명부 시점의 위원 표기이며 감사 당일 출석이 아닙니다. 위원이라는 사실이 그 의원이 특정
              피감기관을 질의했다는 뜻도 아닙니다. 위원회 이름은 공식 표기와 정확히 일치할 때만 연결하며,
              이전·변경된 위원회 이름은 합치지 않아 일부 의원이 빠질 수 있습니다.
            </p>
            <ul className="committee-index">
              {committees.map((committee) => (
                <li key={committee.committee_name} id={committeeAnchor(committee.committee_name)}>
                  <div className="committee-index-heading">
                    <h3>{committee.committee_name}</h3>
                    <span>피감대상 {committee.target_count}건 · 위원 {committee.member_count}명</span>
                  </div>
                  <CommitteeMembers committee={committee} label="위원 명단" />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="gukgam-coverage-strip" aria-label="현재 Civic Intel 공개 범위">
        <div>
          <span className="micro-label">People</span>
          <strong>{peopleCount ?? "—"}</strong>
          <small>현재 공개 Person 기록</small>
        </div>
        <div>
          <span className="micro-label">Organizations</span>
          <strong>{organizationCount ?? "—"}</strong>
          <small>현재 공개 기관 기록</small>
        </div>
        <div>
          <span className="micro-label">Evidence path</span>
          <strong>Claim → Evidence → Source</strong>
          <small>공개 연결은 Evidence trace를 유지</small>
        </div>
      </section>

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

      <section className="gukgam-entry-section" aria-labelledby="gukgam-entry-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Explore</span>
            <h2 id="gukgam-entry-title">어디서 시작할까요?</h2>
          </div>
          <p>그래프 전체를 한 번에 펼치지 않고, 인물이나 기관에서 시작해 필요한 관계만 좁혀 봅니다.</p>
        </div>
        <div className="gukgam-entry-grid">
          <Link className="gukgam-entry" href="/people">
            <span className="entry-index">01</span>
            <strong>인물에서 시작</strong>
            <p>현재 공개된 Person을 선택하고 경력·공직 기록과 Evidence를 읽습니다.</p>
            <span className="entry-action">People <span aria-hidden="true">↗</span></span>
          </Link>
          <Link className="gukgam-entry" href="/organizations">
            <span className="entry-index">02</span>
            <strong>기관에서 시작</strong>
            <p>피감기관으로 이어질 수 있는 공공기관·기관 임원 기록과 공개 Claim을 확인합니다.</p>
            <span className="entry-action">Organizations <span aria-hidden="true">↗</span></span>
          </Link>
          <Link className="gukgam-entry" href="/people">
            <span className="entry-index">03</span>
            <strong>공식 연결 보기</strong>
            <p>Person 상세의 local graph에서 현재 Evidence Core가 지원하는 공식 연결을 확인합니다.</p>
            <span className="entry-action">Connections <span aria-hidden="true">↗</span></span>
          </Link>
        </div>
      </section>

      <section className="gukgam-status-section" aria-labelledby="gukgam-status-title">
        <div>
          <span className="eyebrow">Coverage / source-gated</span>
          <h2 id="gukgam-status-title">국감 전용 자료는<br /><em>검증된 만큼만</em></h2>
          <p>위원회별 계획, 피감기관, 증인·참고인 자료는 공개돼 있다는 이유만으로 바로 수집하지 않습니다. 출처 이용 조건, 버전과 식별자를 확인한 뒤 기존 Evidence Core에 연결합니다.</p>
        </div>
        <ol className="gukgam-status-list">
          <li><span>01</span><div><strong>위원회 계획</strong><p>공식 계획서의 일정·대상기관 구조를 검토한 뒤 반영합니다.</p></div></li>
          <li><span>02</span><div><strong>피감기관</strong><p>기존 canonical Organization과 정확히 연결되는 경우에만 기관 관계를 확장합니다.</p></div></li>
          <li><span>03</span><div><strong>증인·참고인</strong><p>공식 명단의 이름만으로 Person을 만들거나 합치지 않습니다.</p></div></li>
        </ol>
      </section>
    </div>
  );
}
