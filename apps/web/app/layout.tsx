import type { Metadata } from "next";
import Link from "next/link";

import { buildRootMetadata, SITE_NAME } from "./site-metadata";
import { readSnapshotAt } from "./public-read";
import "./styles.css";

// Snapshot-backed server layouts must refresh on navigation. The static builder rewrites this.
export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  return buildRootMetadata();
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // HTTP/static uses CIVIC_SNAPSHOT_AT; the Worker uses its request's ACTIVE D1 snapshot.
  const snapshotAt = await readSnapshotAt();
  return (
    <html lang="ko">
      <body>
        <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
        <div className="app-shell">
          <header className="site-header">
            <div className="header-inner">
              <Link className="brand" href="/" aria-label={`${SITE_NAME} 홈`}>
                <span className="brand-mark" aria-hidden="true">국감</span>
                <span className="brand-copy">
                  <strong>{SITE_NAME}</strong>
                  <small>국감 인물 이력·근거 검색</small>
                </span>
              </Link>
              <nav className="global-nav" aria-label="주요 메뉴">
                <Link className="nav-link" href="/people">인물 찾기</Link>
                <Link className="nav-link nav-event-link" href="/gukgam/2026">국감 일정</Link>
                <Link className="nav-link" href="/organizations">기관</Link>
                <Link className="nav-link" href="/#coverage">자료 범위</Link>
              </nav>
            </div>
          </header>
          <main id="main-content">{children}</main>
          <footer className="site-footer">
            <div className="footer-brand">
              <span className="brand-mark small" aria-hidden="true">국감</span>
              <strong>{SITE_NAME}</strong>
            </div>
            <div className="footer-note">
              {snapshotAt && <span>자료 기준 {snapshotAt}</span>}
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
