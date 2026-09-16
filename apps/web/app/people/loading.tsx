export default function PeopleLoading() {
  return (
    <div className="site-page people-page people-loading" aria-busy="true" aria-live="polite">
      <header className="people-header">
        <div>
          <div className="eyebrow">Public discovery / People</div>
          <h1>People</h1>
          <p className="profile-lede">공개된 People을 불러오는 중입니다.</p>
        </div>
      </header>
      <div className="loading-label">Public profiles loading…</div>
      <div className="roster-list" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <div className="roster-row skeleton-row" key={index} />)}
      </div>
    </div>
  );
}
