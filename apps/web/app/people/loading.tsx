export default function PeopleLoading() {
  return (
    <div className="site-page people-page people-loading" aria-busy="true" aria-live="polite">
      <header className="people-header">
        <div>
          <h1>인물 찾기</h1>
          <p className="profile-lede">공개 인물 기록을 불러오는 중입니다.</p>
        </div>
      </header>
      <div className="loading-label">인물 기록 불러오는 중…</div>
      <div className="roster-list" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <div className="roster-row skeleton-row" key={index} />)}
      </div>
    </div>
  );
}
