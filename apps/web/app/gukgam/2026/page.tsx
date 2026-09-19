import type { Metadata } from "next";
import Link from "next/link";

import GukgamSearch from "../../components/gukgam-search";
import ReadState from "../../components/read-state";
import { getOrganizations, getPeople } from "../../data";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "국감 2026",
  description: "2026 국정감사를 인물·기관·공식 기록과 Evidence를 통해 탐색하는 Civic Intel 이벤트 화면",
};

export default async function Gukgam2026Page() {
  const [peopleResult, organizationsResult] = await Promise.all([
    getPeople(),
    getOrganizations(),
  ]);

  const peopleCount = peopleResult.state === "success" ? peopleResult.data.length : null;
  const organizationCount = organizationsResult.state === "success" ? organizationsResult.data.length : null;

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
            <Link className="primary-action" href="/people">인물 탐색 <span aria-hidden="true">↗</span></Link>
            <Link className="inline-action" href="/organizations">기관 탐색 <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
        <aside className="gukgam-method" aria-label="국감 화면의 공개 원칙">
          <span className="micro-label">Launch principle</span>
          <strong>공식 기록상 연결만</strong>
          <p>같은 이름, 같은 학교명 또는 단순한 동시 등장만으로 관계를 만들지 않습니다. 각 연결은 Claim과 Evidence를 따라 원문까지 확인할 수 있어야 합니다.</p>
        </aside>
      </header>

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
        people={
          peopleResult.state === "success"
            ? peopleResult.data.map(({ id, canonical_name, discovery }) => ({
                id,
                canonical_name,
                discovery,
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
