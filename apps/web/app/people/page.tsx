import RosterGrid from "../components/roster-grid";
import ReadState from "../components/read-state";
import { getGukgamWitnesses, getPeople } from "../data";
import { buildPageMetadata } from "../site-metadata";

export const dynamic = "force-dynamic";

export const metadata = buildPageMetadata({
  title: "인물 찾기",
  description: "공개 기준을 통과한 인물 기록을 이름으로 찾고, 역할·이력의 근거와 출처를 확인합니다.",
  path: "/people",
});

export default async function PeoplePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[] }>;
}) {
  const params = await searchParams;
  const initialQuery = typeof params.q === "string" ? params.q.slice(0, 80) : "";
  const [peopleResult, witnessResult] = await Promise.all([getPeople(), getGukgamWitnesses()]);
  // Witness names are source-listed text; only display fields are passed, never IDs beyond the Claim anchor.
  const witnesses = witnessResult.state === "success"
    ? witnessResult.data.items.map((item) => ({
        claimId: item.claim_id,
        name: item.name,
        affiliationTitle: item.affiliation_title,
        committeeName: item.committee_name,
        category: item.category,
        attendanceDateText: item.attendance_date_text,
        sourceTag: item.source_tag,
        officiallyPublished: item.acquisition_channel !== "OWNER_SUPPLIED_COPY",
      }))
    : [];

  return (
    <div className="site-page people-page">
      <header className="people-header">
        <div>
          <h1>인물 찾기</h1>
          <p className="profile-lede">국회의원과 국감 관련 인물의 공개 기록을 이름으로 찾습니다. 이름이 같아도 다른 사람이면 따로 보여줍니다.</p>
        </div>
      </header>

      {peopleResult.state === "success" ? (
        peopleResult.data.length > 0 ? (
          <section className="directory-section" aria-labelledby="people-list-title">
            <h2 className="sr-only" id="people-list-title">인물 목록 {peopleResult.data.length}명</h2>
            <RosterGrid people={peopleResult.data} initialQuery={initialQuery} witnesses={witnesses} />
          </section>
        ) : (
          <p className="empty-state" role="status">
            <span><strong>현재 공개 인물 기록이 없습니다.</strong><small>대상이 없다는 의미가 아니라 현재 공개 조건의 결과가 비어 있다는 뜻입니다.</small></span>
          </p>
        )
      ) : (
        <ReadState error={peopleResult.error} />
      )}
    </div>
  );
}
