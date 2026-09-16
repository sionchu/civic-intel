import type { Metadata } from "next";

import RosterGrid from "../components/roster-grid";
import ReadState from "../components/read-state";
import { getPeople } from "../data";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "People",
  description: "현재 공개된 resolved Person을 근거와 함께 탐색합니다.",
};

export default async function PeoplePage() {
  const peopleResult = await getPeople();

  return (
    <div className="site-page people-page">
      <header className="people-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> Public discovery / Resolved people</div>
          <h1>People</h1>
          <p className="profile-lede">현재 공개된 canonical Person을 이름과 확인 가능한 국회 기본 프로필로 탐색합니다. 각 카드는 evidence dossier로 이어집니다.</p>
        </div>
        <div className="profile-stamp" aria-hidden="true">
          <span className="micro-label">PUBLIC DIRECTORY</span>
          <strong>PEOPLE</strong>
          <span>read-only / current</span>
        </div>
      </header>

      {peopleResult.state === "success" ? (
        peopleResult.data.length > 0 ? (
          <section className="directory-section" aria-labelledby="people-list-title">
            <div className="section-intro">
              <div>
                <span className="eyebrow">Canonical people</span>
                <h2 id="people-list-title">Evidence-backed profiles</h2>
              </div>
              <p>사람을 선택하면 현재 published Claim과 ClaimEvidence, Source policy를 함께 확인할 수 있습니다.</p>
            </div>
            <RosterGrid people={peopleResult.data} />
          </section>
        ) : (
          <p className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <span><strong>현재 공개 People이 없습니다.</strong><small>대상이 없다는 의미가 아니라 현재 공개 조건의 결과가 비어 있다는 뜻입니다.</small></span>
          </p>
        )
      ) : (
        <ReadState error={peopleResult.error} />
      )}
    </div>
  );
}
