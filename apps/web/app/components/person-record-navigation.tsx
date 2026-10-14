import { recordHref, type RecordQuery } from "../person-record-window";

export default function PersonRecordNavigation({ query, name, total, page, anchor, search, committeeOptions, actualCount }: {
  query: RecordQuery; name: string; total: number; page: number; anchor: string;
  search?: { name: string; label: string }; committeeOptions?: string[]; actualCount?: number;
}) {
  const pages = Math.ceil(total / 20);
  page = Math.min(page, Math.max(1, pages));
  const shown = Math.max(0, Math.min(20, total - (page - 1) * 20));
  return <>
    {search && <form method="get" action={`#${anchor}`} className="vote-filters">
      {Object.entries(query).filter(([key]) => ![search.name, name, "claim", "source", ...(committeeOptions ? ["committee"] : [])].includes(key)).map(([key, value]) => <input type="hidden" key={key} name={key} value={value} />)}
      <label>{search.label}<input type="search" name={search.name} defaultValue={query[search.name] ?? ""} maxLength={160} placeholder="제목에 포함된 단어" /></label>
      {committeeOptions && <label>소관위원회<select name="committee" defaultValue={query.committee ?? "ALL"}><option value="ALL">전체</option>{committeeOptions.map((item) => <option key={item}>{item}</option>)}<option value="UNKNOWN">소관위원회 미기재</option></select></label>}
      <button className="load-more" type="submit">검색</button>
    </form>}
    <p className="section-note" role="status">검색 범위 {total.toLocaleString("ko-KR")}건 · 현재 {actualCount ?? shown}건 표시{pages > 0 && ` · ${page}/${pages}쪽`}{actualCount !== undefined && ` · 이 쪽의 대상 ${shown}건 (별도 선택한 출처 포함, 조회 실패 제외)`}</p>
    {pages > 1 && <nav className="source-links" aria-label={`${anchor} 기록 페이지`}>
      {page > 1 && <a href={recordHref(query, { [name]: String(page - 1) }, anchor)}>이전 기록</a>}
      {page < pages && <a href={recordHref(query, { [name]: String(page + 1) }, anchor)}>다음 기록</a>}
    </nav>}
  </>;
}
