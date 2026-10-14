import Link from "next/link";
import { getPeople, getPerson } from "../../data";
import ReadState from "../../components/read-state";
import { compareVotes, evidenceHref, PAGE_SIZE } from "./comparison";

export const dynamic = "force-dynamic";
export const metadata = { title: "두 인물의 표결 기록 비교 | 모두의국감" };
type Params = Record<string, string | string[] | undefined>;
const scalar = (p: Params, name: string) => typeof p[name] === "string" ? p[name] as string : "";

export default async function VoteComparisonPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const leftId = scalar(params, "left"), rightId = scalar(params, "right");
  const start = scalar(params, "start"), end = scalar(params, "end");
  const people = await getPeople();
  if (people.state === "error") return <div className="site-page"><h1>표결 기록 비교</h1><ReadState error={people.error} /></div>;
  const options = people.data.filter((p) => p.identity_status === "RESOLVED");
  let result: Awaited<ReturnType<typeof compareVotes>> | null = null;
  let message = "";
  let failure = null;
  if (leftId || rightId || start || end) {
    if (!options.some((p) => p.id === leftId) || !options.some((p) => p.id === rightId)) message = "목록에서 두 공개 인물을 선택해 주세요.";
    else {
      const [a, b] = await Promise.all([getPerson(leftId), getPerson(rightId)]);
      if (a.state === "error") failure = a.error;
      else if (b.state === "error") failure = b.error;
      else {
        try { result = await compareVotes(a.data, b.data, start, end); }
        catch (error) { message = error instanceof Error ? error.message : "비교 조건을 확인해 주세요."; }
      }
    }
  }
  const requestedVersion = scalar(params, "v");
  const drift = Boolean(result && requestedVersion && requestedVersion !== result.version);
  const rawPage = scalar(params, "page");
  const page = /^\d{1,6}$/.test(rawPage) && Number(rawPage) > 0 ? Number(rawPage) : 1;
  const pages = Math.max(1, Math.ceil((result?.common ?? 0) / PAGE_SIZE));
  const outOfRange = Boolean(result && page > pages);
  const pageHref = (n: number) => `/compare/votes?${new URLSearchParams({ left: leftId, right: rightId, start, end, page: String(n), v: result!.version })}#comparison-results`;
  const name = (id: string) => options.find((p) => p.id === id)?.canonical_name ?? "";
  return <div className="site-page">
    <Link href="/people" className="back-link">인물 찾기</Link>
    <h1>두 인물의 표결 기록 비교</h1>
    <p className="lede">같은 기간의 같은 표결에서 두 사람이 어떻게 기록됐는지 확인합니다.</p>
    <form action="/compare/votes" method="get" className="vote-filters">
      {(["left", "right"] as const).map((side, index) => <label key={side} htmlFor={`compare-${side}`}>{index + 1}번째 인물<select id={`compare-${side}`} name={side} defaultValue={side === "left" ? leftId : rightId} required><option value="">인물 선택</option>{options.map((p) => <option key={p.id} value={p.id}>{p.canonical_name}</option>)}</select></label>)}
      <label htmlFor="compare-start">시작일<input id="compare-start" type="date" name="start" defaultValue={start} required /></label>
      <label htmlFor="compare-end">종료일<input id="compare-end" type="date" name="end" defaultValue={end} required /></label>
      <button className="load-more" type="submit">기록 비교</button>
    </form>
    {message && <p role="alert" className="empty-note">{message}</p>}
    {failure && <ReadState error={failure} />}
    {drift && <ReadState error={{ code: "SOURCE_VERSION_CONFLICT", message: "비교 입력이 변경되었습니다. 같은 조건으로 기록 비교를 다시 실행해 주세요.", request_id: null }} />}
    {outOfRange && !drift && <p role="alert">요청한 페이지가 비교 범위를 벗어났습니다. <Link href={pageHref(1)}>첫 페이지</Link></p>}
    {result && !drift && !outOfRange && <section id="comparison-results" aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">{name(leftId)} · {name(rightId)}</h2>
      <p>{start}부터 {end}까지 · <span className="status DERIVED">기록 비교</span></p>
      <p>공통 비교 대상 {result.common}건 · {name(leftId)}에만 연결된 기록 {result.leftOnly}건 · {name(rightId)}에만 연결된 기록 {result.rightOnly}건</p>
      <p className="section-note">양쪽에 공개된 같은 대수·의안·표결시각의 교집합입니다. 미수집 기록은 분모에 포함되지 않으며, 불참은 반대나 불성실을 뜻하지 않습니다.</p>
      {result.common === 0 ? <p className="empty-note">이 조건에서 비교 가능한 공통 표결이 없습니다.</p> : <ol className="vote-rows">{result.rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((row) => <li className="vote-row" key={row.left.key}>
        <time className="vote-date" dateTime={row.left.date}>{row.left.date}</time>
        <div className="vote-bill"><strong>{row.left.title}</strong><small className="claim-date">{row.left.term}대 · 의안 {row.left.billId}{row.left.title !== row.right.title && ` · 다른 쪽 원문 제목: ${row.right.title}`}</small></div>
        <span>{row.different ? "기록 다름" : "기록 같음"}</span>
        <div className="vote-trace source-links">{[{ person: leftId, record: row.left }, { person: rightId, record: row.right }].map(({ person, record }) => <div key={person}><Link href={evidenceHref(person, record)}>{name(person)}: {record.choice} · 근거</Link>{record.sourceIds.map((sourceId, i) => <Link key={sourceId} href={`/people/${encodeURIComponent(person)}?source=${encodeURIComponent(sourceId)}#source-${encodeURIComponent(sourceId)}`}>출처 {i + 1}</Link>)}</div>)}</div>
      </li>)}</ol>}
      {pages > 1 && <nav className="source-links" aria-label="비교 결과 페이지">{page > 1 && <Link href={pageHref(page - 1)}>이전 20건</Link>}<span>{page} / {pages} 페이지</span>{page < pages && <Link href={pageHref(page + 1)}>다음 20건</Link>}</nav>}
      <details><summary>비교 방법과 제외된 입력</summary><p>방법 {result.method}. 정정·철회로 입력이 달라지면 새 결과로 다시 확인합니다.</p>{([{ label: name(leftId), counts: result.leftExcluded }, { label: name(rightId), counts: result.rightExcluded }]).map(({ label, counts }, index) => <p key={index}>{label}: 신원·상태·근거·날짜 등 조건 미충족 {counts.invalid}건, 상충 근거 {counts.conflict}건, 중복 표결키 {counts.duplicate}건, 기간 밖 {counts.outsidePeriod}건.</p>)}<p>인물의 신념·정책성향·출석 사유를 평가하지 않습니다. 원문과 공개 범위를 함께 확인해 주세요.</p><p>입력 버전 <code>{result.version}</code></p></details>
    </section>}
  </div>;
}
