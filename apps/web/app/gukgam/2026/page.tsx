import type { Metadata } from "next";
import Link from "next/link";

import GukgamSearch from "../../components/gukgam-search";
import ReadState from "../../components/read-state";
import { getGukgamTargets, getOrganizations, getPeople } from "../../data";
import { buildPageMetadata } from "../../site-metadata";

export const dynamic = "force-dynamic";

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

  const [peopleResult, organizationsResult, targetsResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
    getGukgamTargets(),
  ]);

  const targetCount = targetsResult.state === "success" ? targetsResult.data.target_count : null;
  const committeeCount = targetsResult.state === "success" ? targetsResult.data.committee_count : null;

  return (
    <div className="site-page gukgam-page">
      <header className="gukgam-hero">
        <div className="gukgam-hero-copy">
          <p className="eyebrow">Civic Intel / Event surface</p>
          <h1>국감 <em>2026</em></h1>
          <p className="lede">
            위원회별 공식 계획서에 올라온 피감기관과 감사일정을 먼저 확인합니다.
            기관장·증인·참고인은 공식 명단과 신원 근거가 확인된 범위에서 연결합니다.
          </p>
          <div className="hero-actions">
            <Link className="primary-action" href="#gukgam-published-targets-title">피감기관 보기 <span aria-hidden="true">↓</span></Link>
            <Link className="inline-action" href="/organizations">기관 탐색 <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
        <aside className="gukgam-method" aria-label="국감 화면의 공개 원칙">
          <span className="micro-label">Launch principle</span>
          <strong>공식 기록상 연결만</strong>
          <p>피감기관은 감사 대상 기관입니다. 기관증인·일반증인·참고인은 각 공식 출석 명단으로 구분합니다. 국회의원 명부는 감사 주체의 기록입니다.</p>
          <p>같은 이름, 같은 학교명 또는 단순한 동시 등장만으로 관계를 만들지 않습니다. 각 연결은 Claim과 Evidence를 따라 원문까지 확인할 수 있어야 합니다.</p>
        </aside>
      </header>

      <section className="gukgam-coverage-strip" aria-label="현재 국감 피감기관 공개 범위">
        <div>
          <span className="micro-label">피감기관 일정</span>
          <strong>{targetCount ?? "—"}</strong>
          <small>공개 Claim으로 연결된 건수 · 같은 기관의 여러 일정 포함</small>
        </div>
        <div>
          <span className="micro-label">위원회</span>
          <strong>{committeeCount ?? "—"}</strong>
          <small>현재 공개된 피감기관 일정이 있는 위원회</small>
        </div>
        <div>
          <span className="micro-label">Evidence path</span>
          <strong>Claim → Evidence → Source</strong>
          <small>공개 연결은 Evidence trace를 유지</small>
        </div>
      </section>

      {peopleResult.state === "error" && <ReadState error={peopleResult.error} />}
      {organizationsResult.state === "error" && <ReadState error={organizationsResult.error} />}

      <section className="gukgam-entry-section" aria-labelledby="gukgam-published-targets-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Published / Claim-backed</span>
            <h2 id="gukgam-published-targets-title">공개된 피감기관</h2>
          </div>
          <p>
            공식 계획서의 피감대상 가운데 canonical Organization에 검토 연결되고
            published Claim과 Evidence까지 갖춘 일정만 표시합니다.
          </p>
        </div>

        {targetsResult.state === "error" ? (
          <ReadState error={targetsResult.error} />
        ) : targetsResult.data.items.length === 0 ? (
          <div className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <div>
              <strong>현재 공개된 피감기관 Claim이 없습니다.</strong>
              <p>
                감사대상이 없다는 뜻이 아니라, 현재 공개 기준을 통과한 Claim이 아직 없다는 뜻입니다.
              </p>
            </div>
          </div>
        ) : (
          <div className="organization-claim-list">
            {targetsResult.data.items.map((item) => (
              <article className="claim organization-claim-card" key={item.claim_id}>
                <div className="claim-heading">
                  <span className="claim-kind">GUKGAM AUDIT PLAN</span>
                  <span className="status FACT">FACT</span>
                </div>
                <div className="organization-claim-meta">
                  <span>{item.committee_name}</span>
                  <span>감사일정 {item.audit_date}</span>
                  <span>계획서 공개 {item.source_published_date}</span>
                </div>
                <h3 className="claim-title">{item.organization.name}</h3>
                <p className="resolution">
                  공식 계획서상 피감대상 · {item.section}
                  {item.time_text ? ` · ${item.time_text}` : ""}
                  {item.venue ? ` · ${item.venue}` : ""}
                </p>
                <Link
                  className="inline-action"
                  href={`/organizations/${item.organization.id}#claims`}
                >
                  기관 Claim / Evidence 보기 <span aria-hidden="true">↗</span>
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
              </article>
            ))}
          </div>
        )}

        {targetsResult.state === "success" && (
          <p className="gukgam-search-share-note">
            현재 공개 범위 {targetsResult.data.target_count}건 · published Claim only ·
            전체 감사대상 목록이 아닙니다. 미공개·미연결 대상은 추정해 채우지 않습니다.
          </p>
        )}
      </section>

      {peopleResult.state === "success" && organizationsResult.state === "success" && (
        <GukgamSearch
          initialQuery={initialQuery}
          people={peopleResult.data.map(({ id, canonical_name, discovery }) => ({
            id,
            canonical_name,
            discovery,
          }))}
          organizations={organizationsResult.data}
        />
      )}

      <section className="gukgam-entry-section" aria-labelledby="gukgam-entry-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Explore</span>
            <h2 id="gukgam-entry-title">어디서 시작할까요?</h2>
          </div>
          <p>피감기관의 공식 일정과 근거부터 읽고, 기관과 관련 인물의 공개 기록으로 이어갑니다. 인물 검색은 기존 공개 기록 탐색입니다.</p>
        </div>
        <div className="gukgam-entry-grid">
          <Link className="gukgam-entry" href="/organizations">
            <span className="entry-index">01</span>
            <strong>기관에서 시작</strong>
            <p>기관의 현재 공개 Claim과 출처를 읽고 공식 계획서상 감사대상 여부를 확인합니다.</p>
            <span className="entry-action">Organizations <span aria-hidden="true">↗</span></span>
          </Link>
          <Link className="gukgam-entry" href="/people">
            <span className="entry-index">02</span>
            <strong>인물 기록 보기</strong>
            <p>신원이 확인된 Person의 경력·공직 기록을 읽습니다. 증인·참고인 구분은 공식 명단을 따릅니다.</p>
            <span className="entry-action">People <span aria-hidden="true">↗</span></span>
          </Link>
          <Link className="gukgam-entry" href="#gukgam-published-targets-title">
            <span className="entry-index">03</span>
            <strong>감사대상 근거 보기</strong>
            <p>공개된 피감기관 일정에서 Claim·Evidence·Source를 따라 공식 계획서의 근거를 확인합니다.</p>
            <span className="entry-action">Evidence <span aria-hidden="true">↑</span></span>
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
