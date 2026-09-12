import Link from "next/link";

import RosterGrid from "./components/roster-grid";
import { getPeople } from "./data";

export const dynamic = "force-dynamic";

export default async function RosterPage() {
  const people = await getPeople();

  return (
    <div className="site-page home-page">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> Evidence Directory / V0</div>
          <h1 id="hero-title">공개 기록을<br /><em>증거로 읽는 사람들</em></h1>
          <p className="lede">공개된 기록을 따라가며, 확인된 것과 아직 열려 있는 것을 분리합니다. 모든 프로필은 canonical identity와 published evidence에서 시작합니다.</p>
          <div className="hero-actions">
            <a className="primary-action" href="#roster">Roster 살펴보기 <span aria-hidden="true">↘</span></a>
            <span className="hero-note"><span className="signal-dot" /> Source-traceable / read-only</span>
          </div>
        </div>
        <div className="hero-panel" aria-label="Evidence Directory 읽는 방법">
          <div className="panel-topline"><span className="micro-label">How to read</span><span className="panel-index">01 / 03</span></div>
          <div className="panel-visual" aria-hidden="true">
            <span className="panel-ring ring-one" />
            <span className="panel-ring ring-two" />
            <span className="panel-dot dot-one" />
            <span className="panel-dot dot-two" />
            <span className="panel-cross">+</span>
          </div>
          <p className="panel-title">사람 → 주장 → 근거 → 출처</p>
          <p className="panel-copy">한 번에 결론을 내리지 않고, 공개된 근거의 경로를 먼저 보여줍니다.</p>
          <Link className="text-link" href="#principles">읽는 원칙 <span aria-hidden="true">↗</span></Link>
        </div>
      </section>

      <section className="signal-strip" aria-label="Directory 개요">
        <div className="signal-cell signal-primary">
          <span className="micro-label">Public roster</span>
          <strong>{people.length}</strong>
          <span>resolved identities</span>
        </div>
        <div className="signal-cell">
          <span className="micro-label">Epistemic posture</span>
          <strong>Explicit</strong>
          <span>FACT · CLAIM · UNKNOWN</span>
        </div>
        <div className="signal-cell">
          <span className="micro-label">Publication rule</span>
          <strong>Trace first</strong>
          <span>Claim → Evidence → Source</span>
        </div>
      </section>

      <section className="directory-section" id="roster" aria-labelledby="roster-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">Public roster</span>
            <h2 id="roster-title">Resolved people</h2>
          </div>
          <p>현재 공개 디렉터리에는 자동으로 확인된 identity만 표시됩니다. 이름을 선택하면 해당 profile의 근거 경로를 볼 수 있습니다.</p>
        </div>
        <RosterGrid people={people} />
      </section>

      <section className="principles" id="principles" aria-labelledby="principles-title">
        <div className="principles-heading">
          <span className="eyebrow">Reading notes</span>
          <h2 id="principles-title">읽는 순서가<br /><em>곧 신뢰의 구조</em>입니다.</h2>
        </div>
        <div className="principles-list">
          <div className="principle"><span>01</span><div><strong>Identity first</strong><p>Person은 resolved canonical identity가 있을 때만 공개 roster에 나타납니다.</p></div></div>
          <div className="principle"><span>02</span><div><strong>Status stays visible</strong><p>FACT, CLAIM, UNKNOWN과 SOURCE CONFLICT를 숨기지 않습니다.</p></div></div>
          <div className="principle"><span>03</span><div><strong>Evidence stays close</strong><p>각 항목에서 ClaimEvidence와 Source policy를 바로 따라갈 수 있습니다.</p></div></div>
        </div>
      </section>
    </div>
  );
}
