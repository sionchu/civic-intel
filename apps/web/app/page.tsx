import Link from "next/link";

import ReadState from "./components/read-state";
import { getPeople } from "./data";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const peopleResult = await getPeople();
  const peopleCount = peopleResult.state === "success" ? peopleResult.data.length : null;

  return (
    <div className="site-page home-page">
      <section className="home-intro" aria-labelledby="hero-title">
        <div className="home-intro-copy">
          <p className="eyebrow">Civic Intel / 공개 기록 디렉터리</p>
          <h1 id="hero-title">공개 기록을<br /><em>직접 확인하세요.</em></h1>
          <p className="lede">공개된 사람 기록을 읽고, 어떤 내용이 어디에서 확인되는지 따라갈 수 있습니다. 이곳은 결론을 대신 내리는 곳이 아니라 기록을 살펴보는 읽기 화면입니다.</p>
          <div className="hero-actions">
            <Link className="primary-action" href="/people">사람 기록 탐색 <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
        <aside className="home-coverage" aria-label="현재 공개 범위">
          <div className="home-coverage-heading">
            <span className="micro-label">현재 공개 범위</span>
            <span className="coverage-index">READ-ONLY</span>
          </div>
          {peopleResult.state === "success" ? (
            <>
              <p className="coverage-value"><strong>{peopleCount}</strong><span>명</span></p>
              <p className="coverage-caption">현재 공개된 사람 기록</p>
              {peopleCount === 0 && <p className="coverage-note">현재 공개 조건에서 표시할 사람이 없습니다.</p>}
            </>
          ) : (
            <>
              <p className="coverage-value coverage-unavailable">—</p>
              <p className="coverage-caption">공개 범위를 불러오지 못했습니다.</p>
            </>
          )}
        </aside>
      </section>

      {peopleResult.state === "error" && <div className="home-read-state"><ReadState error={peopleResult.error} /></div>}

      <section className="directory-invite" aria-labelledby="directory-invite-title">
        <div>
          <p className="eyebrow">People / current public directory</p>
          <h2 id="directory-invite-title">사람 탐색</h2>
          <p>이름과 공개 기록에서 확인되는 정당·지역구·위원회·초선/재선 정보로 사람을 찾아보세요.</p>
        </div>
        <Link className="inline-action" href="/people">current public directory <span aria-hidden="true">↗</span></Link>
      </section>

      <section className="principles" id="principles" aria-labelledby="principles-title">
        <div className="principles-heading">
          <span className="eyebrow">Reading method</span>
          <h2 id="principles-title">Civic Intel이<br /><em>기록을 읽는 방식</em></h2>
          <p>사람에서 출처까지, 공개된 근거의 연결을 한 단계씩 확인합니다.</p>
        </div>
        <ol className="principles-list">
          <li className="principle"><span>01</span><div><strong>Identity</strong><p>먼저 공개 기록이 가리키는 사람을 구분합니다. 같은 이름의 기록도 서로 섞지 않습니다.</p></div></li>
          <li className="principle"><span>02</span><div><strong>Evidence</strong><p>표시된 내용 옆에서 Claim과 Evidence를 확인하고, 비어 있거나 열린 상태도 그대로 둡니다.</p></div></li>
          <li className="principle"><span>03</span><div><strong>Source</strong><p>근거가 연결된 출처와 기준일을 따라가며 원문과 기록의 범위를 확인합니다.</p></div></li>
        </ol>
      </section>
    </div>
  );
}
