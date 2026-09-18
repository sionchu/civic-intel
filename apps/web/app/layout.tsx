import type { Metadata } from "next";
import Link from "next/link";

import "./styles.css";

export const metadata: Metadata = {
  title: {
    default: "Civic Intel — Evidence Directory",
    template: "%s — Civic Intel",
  },
  description: "공개 기록과 근거를 따라가는 Civic Intel Evidence Directory",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>
        <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
        <div className="app-shell">
          <header className="site-header">
            <div className="header-inner">
              <Link className="brand" href="/" aria-label="Civic Intel 홈">
                <span className="brand-mark" aria-hidden="true">CI</span>
                <span className="brand-copy">
                  <strong>Civic Intel</strong>
                  <small>Evidence Directory</small>
                </span>
              </Link>
              <nav className="global-nav" aria-label="주요 메뉴">
                <Link className="nav-link" href="/people">People</Link>
                <Link className="nav-link" href="/organizations">Organizations</Link>
                <Link className="nav-link nav-event-link" href="/gukgam/2026">국감 2026</Link>
                <span className="nav-status">읽기 전용 공개 기록</span>
              </nav>
            </div>
          </header>
          <main id="main-content">{children}</main>
          <footer className="site-footer">
            <div className="footer-brand">
              <span className="brand-mark small" aria-hidden="true">CI</span>
              <div>
                <strong>Civic Intel</strong>
                <p>공개 기록과 근거를 함께 보여줍니다.</p>
              </div>
            </div>
            <div className="footer-note">
              <span className="micro-label">PUBLIC / READ-ONLY</span>
              <span>Evidence Directory v0</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
