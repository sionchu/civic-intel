import type { Metadata } from "next";
import Link from "next/link";

import ReadState from "../components/read-state";
import { getOrganizations } from "../data";
import { buildPageMetadata } from "../site-metadata";

export const dynamic = "force-dynamic";

export const metadata = buildPageMetadata({
  title: "기관",
  description: "현재 공개된 기관 기록, 임원 공시와 Evidence를 탐색합니다.",
  path: "/organizations",
});

export default async function OrganizationsPage() {
  const organizationsResult = await getOrganizations();

  return (
    <div className="site-page organizations-page">
      <header className="people-header">
        <h1>기관</h1>
        <p className="profile-lede">
          공공기관과 공시된 임원 현황입니다.
        </p>
      </header>

      {organizationsResult.state === "error" ? (
        <ReadState error={organizationsResult.error} />
      ) : organizationsResult.data.length === 0 ? (
        <p className="empty-state" role="status">
          <span><strong>아직 공개된 기관 기록이 없습니다.</strong></span>
        </p>
      ) : (
        <section className="directory-section" aria-labelledby="organization-list-title">
          <h2 className="list-count" id="organization-list-title">기관 {organizationsResult.data.length}곳</h2>
          <div className="organization-list">
            {organizationsResult.data.map((organization) => (
              <Link
                className="organization-row"
                href={`/organizations/${organization.id}`}
                key={organization.id}
                aria-label={`${organization.name} · 기관 기록`}
              >
                <span className="organization-row-main">
                  <strong>{organization.name}</strong>
                  <span>{organization.classification ?? "분류 공개 정보 없음"}</span>
                </span>
                <span className="organization-row-facts">
                  <span><small>현재 임원 공개</small><strong>{organization.executive_count}건</strong></span>
                  <span><small>공개 기록</small><strong>{organization.published_claim_count}건</strong></span>
                </span>
                <span className="row-proof">근거 {organization.evidence_count}개{organization.as_of ? ` · 기준일 ${organization.as_of}` : ""}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
