import type { Metadata } from "next";

import OrganizationDirectory from "../components/organization-directory";
import ReadState from "../components/read-state";
import { getOrganizations } from "../data";
import { buildPageMetadata } from "../site-metadata";

export const dynamic = "force-dynamic";

export const metadata = buildPageMetadata({
  title: "Organizations",
  description: "현재 공개된 기관 기록, 임원 공시와 Evidence를 탐색합니다.",
  path: "/organizations",
});

export default async function OrganizationsPage() {
  const organizationsResult = await getOrganizations();

  return (
    <div className="site-page organizations-page">
      <header className="people-header">
        <div className="eyebrow">Public discovery / Organizations</div>
        <h1>Organizations</h1>
        <p className="profile-lede">
          현재 공개 Claim이 연결된 기관 기록을 분류와 공개된 임원현황 내용으로 탐색합니다.
          기관별 상세 화면에서 Claim, Evidence와 출처를 이어서 확인할 수 있습니다.
        </p>
      </header>

      {organizationsResult.state === "error" ? (
        <ReadState error={organizationsResult.error} />
      ) : organizationsResult.data.length === 0 ? (
        <p className="empty-state" role="status">
          <span className="empty-state-mark" aria-hidden="true">∅</span>
          <span><strong>현재 공개 기관 기록이 없습니다.</strong><small>현재 공개 Claim이 연결된 기관만 표시합니다.</small></span>
        </p>
      ) : (
        <section className="directory-section" aria-labelledby="organization-list-title">
          <div className="section-intro">
            <div>
              <span className="eyebrow">Current public directory</span>
              <h2 id="organization-list-title">{organizationsResult.data.length}개의 공개 기관 기록</h2>
            </div>
            <p>기관을 선택하면 공개된 Claim, Evidence와 출처를 확인할 수 있습니다.</p>
          </div>
          <OrganizationDirectory organizations={organizationsResult.data} />
        </section>
      )}
    </div>
  );
}
