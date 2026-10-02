import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getPerson, getPersonOntology, getSource } from "../../data";
import OntologyLocalGraph from "../../components/ontology-local-graph";
import ReadState from "../../components/read-state";
import { getReviewedPortrait } from "../../portrait";
import { buildPageMetadata } from "../../site-metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const result = await getPerson(id);
  if (result.state === "error") {
    return buildPageMetadata({
      title: "Person record",
      description: "Civic Intel 공개 Person 기록",
      path: `/people/${id}`,
    });
  }
  return buildPageMetadata({
    title: result.data.canonical_name,
    description: `${result.data.canonical_name}의 공개 기록, Claim, Evidence와 출처를 확인합니다.`,
    path: `/people/${id}`,
  });
}

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const personResult = await getPerson(id);
  if (personResult.state === "error") {
    if (personResult.error.code === "PUBLIC_RECORD_NOT_FOUND") notFound();
    return (
      <div className="site-page profile-page person-dossier">
        <Link href="/people" className="back-link"><span aria-hidden="true">←</span> 인물 목록</Link>
        <ReadState error={personResult.error} />
      </div>
    );
  }
  const person = personResult.data;
  const [portrait, ontologyResult] = await Promise.all([
    getReviewedPortrait(person),
    getPersonOntology(id),
  ]);
  const ontology = ontologyResult.state === "success" ? ontologyResult.data : null;

  const sectionSourceIds =
    person.profile?.sections.flatMap((section) =>
      section.entries.flatMap((entry) => entry.source_ids),
    ) ?? [];
  const claimSourceIds = (person.claims ?? []).flatMap((claim) => claim.source_ids);
  const ontologySourceIds = ontology?.edges.flatMap((edge) => edge.source_ids) ?? [];
  const sourceIds = [...new Set([...sectionSourceIds, ...claimSourceIds, ...ontologySourceIds])];
  const sourceResults = await Promise.all(sourceIds.map(getSource));
  const sources = sourceResults.flatMap((item) => item.state === "success" ? [item.data] : []);
  const sourceError = sourceResults.find((item) => item.state === "error");
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const sourceTitleById = Object.fromEntries(sources.map((source) => [source.id, source.title]));
  const profile = person.profile;

  return (
    <div className="site-page profile-page person-dossier">
      <Link href="/people" className="back-link"><span aria-hidden="true">←</span> 인물 목록</Link>
      <header className="profile-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✦</span> 공개 인물 기록</div>
          <div className="profile-title-row">
            <h1>{person.canonical_name}</h1>
            <span className="profile-identity"><span className="micro-label">신원 상태</span><span className={`status identity ${person.identity_status}`}>{person.identity_status}</span></span>
          </div>
          <p className="profile-lede">이 인물에 연결된 공개 기록을 영역별로 정리했습니다. 각 항목에서 Claim과 Evidence를 거쳐 출처까지 이어서 확인할 수 있고, 확인되지 않은 부분은 UNKNOWN·PARTIAL 상태로 그대로 표시합니다.</p>
        </div>
        {portrait ? (
          <figure className="profile-portrait">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={portrait.local_path}
              width={portrait.source_width}
              height={portrait.source_height}
              alt={`${person.canonical_name} 공개 사진`}
            />
            <figcaption className="portrait-credit">
              <span>사진: <a href={portrait.source_page_url} target="_blank" rel="noreferrer">{portrait.creator} · Wikimedia Commons</a> · <a href={portrait.license_url} target="_blank" rel="noreferrer">{portrait.license}</a></span>
              <details className="audit-details">
                <summary>사진 출처 감사 정보</summary>
                <small>
                  파일 {portrait.file_title}<br />
                  원본 수정 시각 {portrait.source_revision_timestamp}<br />
                  SHA-1 {portrait.source_sha1}<br />
                  {portrait.modification_note}
                </small>
              </details>
            </figcaption>
          </figure>
        ) : (
          <div className="profile-stamp" aria-hidden="true">
            <span className="micro-label">PUBLIC RECORD</span>
            <strong>CI</strong>
            <span>directory / 01</span>
          </div>
        )}
      </header>

      {profile ? (
        <div className="profile-layout">
          <aside className="profile-index" aria-label="기록 영역 목차">
            <div className="index-heading"><span className="micro-label">기록 목차</span><span>{profile.sections.length}개 영역</span></div>
            <nav>
              <ol>
                {profile.sections.map((section, index) => (
                  <li key={section.id}>
                    <a href={`#section-${section.id}`}>
                      <span className="index-number">{String(index + 1).padStart(2, "0")}</span>
                      <span>{section.label}</span>
                      <span className={`status ${section.status}`}>{section.status}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
            <a className="profile-source-index-link" href="#official-connections">공식 연결</a>
            <a className="profile-source-index-link" href="#sources-title">근거 출처 목록</a>
          </aside>

          <div className="profile-content">
            <section className="coverage-overview profile-coverage" aria-labelledby="coverage-title">
              <div className="overview-heading">
                <span className="eyebrow">기록 범위</span>
                <h2 id="coverage-title">{profile.profile_kind === "ASSEMBLY_MEMBER" ? "이 국회의원 기록에서 확인할 수 있는 범위" : "이 디렉터리 기록에서 확인할 수 있는 범위"}</h2>
                <p>공개된 Claim·Evidence가 있는 영역과 아직 검토된 근거가 없는 영역을 나눠 보여 줍니다. UNKNOWN은 사실이 없다는 뜻이 아니라 근거가 아직 확인되지 않았다는 뜻입니다.</p>
              </div>
              <dl className="profile-coverage-rows">
                <div><dt><span className="status AVAILABLE">AVAILABLE</span></dt><dd><strong>{profile.coverage.available}</strong><span>항목이 있는 영역</span></dd></div>
                <div><dt><span className="status PARTIAL">PARTIAL</span></dt><dd><strong>{profile.coverage.partial}</strong><span>제한이 있는 영역</span></dd></div>
                <div><dt><span className="status UNKNOWN">UNKNOWN</span></dt><dd><strong>{profile.coverage.unknown}</strong><span>근거가 아직 없는 영역</span></dd></div>
              </dl>
            </section>

            <div className="profile-sections">
              {profile.sections.map((section) => (
                <section className="profile-section" key={section.id} id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`}>
                  <div className="section-heading">
                    <div><span className="section-index">{String(profile.section_order.indexOf(section.id) + 1).padStart(2, "0")}</span><h2 id={`heading-${section.id}`}>{section.label}</h2></div>
                    <span className={`status ${section.status}`}>{section.status}</span>
                  </div>
                  {section.note && <p className="section-note">{section.note}</p>}
                  {section.entries.length === 0 ? (
                    <p className="empty profile-empty-row"><span className="status UNKNOWN">UNKNOWN</span> <span>이 영역에는 아직 검토된 공개 항목이 없습니다. 기록이 없다는 뜻은 아닙니다.</span></p>
                  ) : (
                    section.entries.map((entry) => {
                      const changeDetails = entry.kind === "CHANGE" ? entry.details as {
                        method_version?: string;
                        derived_reason?: string;
                        earlier?: { claim_id?: string; date?: string; predicate?: string; role_text?: string };
                        later?: { claim_id?: string; date?: string; predicate?: string; role_text?: string };
                        input_scope?: { correction_semantics?: string; provider_record_identity?: string };
                        coverage?: { eligible_claim_count?: number; comparison?: string };
                        limitations?: string[];
                      } : null;
                      const isLegislativeActivity = !changeDetails && entry.details.predicate === "ASSEMBLY_BILL_PARTICIPATION";
                      const activityRole = isLegislativeActivity && typeof entry.details.participation_role === "string"
                        ? entry.details.participation_role === "REPRESENTATIVE_PROPOSER" ? "대표 발의" : "공동 발의"
                        : null;
                      const activityTitle = isLegislativeActivity && typeof entry.details.object_text === "string"
                        ? entry.details.object_text
                        : null;
                      return (
                      <article className={`claim${changeDetails ? " change-card" : ""}`} key={entry.id}>
                        <div className="claim-heading">
                          <span className="claim-kind">{changeDetails ? "파생 비교 · CHANGE" : entry.kind}</span>
                          {entry.epistemic_status && <span className={`status ${entry.epistemic_status}`}>{entry.epistemic_status}</span>}
                        </div>
                        {!changeDetails && entry.source_conflict && (
                          <div className="conflict-note">
                            <span className="status CONFLICT">SOURCE CONFLICT</span>
                            <span>서로 다른 근거가 상충하며 자동으로 어느 한쪽을 진실로 판정하지 않습니다.</span>
                          </div>
                        )}
                        {changeDetails ? (
                          <>
                            <p className="claim-title">{entry.title}</p>
                            <div className="change-sequence" aria-label="날짜순 비교">
                              <div className="change-point">
                                <span className="micro-label">이전 · {changeDetails.earlier?.date ?? "UNKNOWN"}</span>
                                <strong>{changeDetails.earlier?.role_text ?? "표시값 없음"}</strong>
                                <small>{changeDetails.earlier?.predicate ?? "UNKNOWN"} · Claim {changeDetails.earlier?.claim_id ?? "UNKNOWN"}</small>
                              </div>
                              <span className="change-arrow" aria-hidden="true">→</span>
                              <div className="change-point later">
                                <span className="micro-label">이후 · {changeDetails.later?.date ?? "UNKNOWN"}</span>
                                <strong>{changeDetails.later?.role_text ?? "표시값 없음"}</strong>
                                <small>{changeDetails.later?.predicate ?? "UNKNOWN"} · Claim {changeDetails.later?.claim_id ?? "UNKNOWN"}</small>
                              </div>
                            </div>
                            {changeDetails.derived_reason && <p className="change-reason">{changeDetails.derived_reason}</p>}
                            <details className="audit-details">
                              <summary>비교 방법과 범위</summary>
                              <small>
                                방법 버전 {changeDetails.method_version ?? "UNKNOWN"}<br />
                                입력 범위 {changeDetails.input_scope?.provider_record_identity ?? "UNKNOWN"}<br />
                                정정 처리 방식 {changeDetails.input_scope?.correction_semantics ?? "UNKNOWN"}<br />
                                비교 가능한 입력 {changeDetails.coverage?.eligible_claim_count ?? "UNKNOWN"}<br />
                                {changeDetails.coverage?.comparison ?? "비교 규칙 정보 없음"}<br />
                                {(changeDetails.limitations ?? []).map((item) => <span key={item}>{item}<br /></span>)}
                              </small>
                            </details>
                          </>
                        ) : isLegislativeActivity ? (
                          <>
                            <div className="activity-badges">
                              <span className="status AVAILABLE">{activityRole}</span>
                              <span className="claim-kind">국회 공식 의안 기록</span>
                            </div>
                            <p className="claim-title">{activityTitle ?? entry.title}</p>
                            <p className="activity-assertion">{entry.title}</p>
                            {entry.date && <small className="claim-date">발의일 {entry.date}</small>}
                            <dl className="activity-facts">
                              {typeof entry.details.bill_no === "string" && <div><dt>의안번호</dt><dd>{entry.details.bill_no}</dd></div>}
                              {typeof entry.details.committee === "string" && <div><dt>소관 위원회</dt><dd>{entry.details.committee}</dd></div>}
                              {typeof entry.details.process_result === "string" && <div><dt>처리 결과·상태</dt><dd>{entry.details.process_result}</dd></div>}
                            </dl>
                            {typeof entry.details.detail_url === "string" && <a className="activity-link" href={entry.details.detail_url} target="_blank" rel="noreferrer">국회 의안 상세 보기 <span aria-hidden="true">↗</span></a>}
                          </>
                        ) : (
                          <>
                            <p className="claim-title">{entry.title}</p>
                            {entry.date && <small className="claim-date">날짜 {entry.date}</small>}
                          </>
                        )}
                        {!changeDetails && typeof entry.details.resolution_note === "string" && entry.details.resolution_note && (
                          <p className="resolution">{entry.details.resolution_note}</p>
                        )}
                        {entry.evidence && entry.evidence.length > 0 ? (
                          <div className="evidence-list">
                            <div className="evidence-list-heading"><strong>근거(Evidence)와 출처</strong><span>{entry.evidence.length}건</span></div>
                            {entry.evidence.map((trace) => {
                              const source = sourceById.get(trace.source_id);
                              return (
                                <div className="evidence-trace" key={trace.id}>
                                  <span className={`status ${trace.stance}`}>{trace.stance}</span>
                                  {source ? <a href={`#source-${source.id}`}>{source.title}</a> : <span>출처 정보를 불러올 수 없음</span>}
                                  <details className="audit-details">
                                    <summary>감사 정보</summary>
                                    <small>
                                      Evidence {trace.id}<br />
                                      Claim {entry.claim_id ?? "해당 없음"}<br />
                                      Source {trace.source_id}<br />
                                      {trace.snapshot_id && <>SourceSnapshot {trace.snapshot_id}<br /></>}
                                      {trace.feeder_observation_id && <>FeederObservation {trace.feeder_observation_id}</>}
                                    </small>
                                  </details>
                                </div>
                              );
                            })}
                          </div>
                        ) : entry.source_ids.length > 0 ? (
                          <div className="source-links">
                            <strong>출처 참조</strong>
                            {entry.source_ids.map((sourceId) => {
                              const source = sourceById.get(sourceId);
                              return <a href={`#source-${sourceId}`} key={sourceId}>{source?.title ?? "출처 기록"}</a>;
                            })}
                          </div>
                        ) : null}
                      </article>
                      );
                    })
                  )}
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="empty-state"><span className="empty-state-mark" aria-hidden="true">∅</span><span><strong>공개 인물 기록 영역을 구성할 수 없습니다.</strong><small><span className="status UNKNOWN">UNKNOWN</span> 영역을 구성할 검토된 공개 근거가 아직 없습니다. 기록이 없다는 뜻은 아닙니다.</small></span></p>
      )}


      <section className="ontology-section" id="official-connections" aria-labelledby="ontology-title">
        <div className="section-intro">
          <div>
            <span className="eyebrow">공식 관계 · 주변 연결</span>
            <h2 id="ontology-title">공식 기록상 연결</h2>
          </div>
          <p>현재 공개된 Claim·Evidence가 직접 뒷받침하는 관계만 보여 줍니다. 그림과 같은 내용을 아래 텍스트 목록으로도 제공합니다.</p>
        </div>
        {ontologyResult.state === "error" ? (
          <ReadState error={ontologyResult.error} />
        ) : ontology && ontology.edges.length > 0 ? (
          <OntologyLocalGraph graph={ontology} sourceTitles={sourceTitleById} />
        ) : (
          <p className="empty-state" role="status">
            <span className="empty-state-mark" aria-hidden="true">∅</span>
            <span><strong>현재 공개 가능한 연결이 없습니다.</strong><small>관계가 없다는 뜻이 아니라, 현재 연결 목록에 표시할 공개 Claim·Evidence가 없다는 뜻입니다.</small></span>
          </p>
        )}
      </section>

      <section className="source-library" aria-labelledby="sources-title">
        <div className="section-intro">
          <div><span className="eyebrow">출처와 감사</span><h2 id="sources-title">이 기록의 출처</h2></div>
          <p>각 출처의 수집·저장·표시 허용 범위를 함께 보여 줍니다. 식별자 같은 세부 정보는 각 출처의 감사 정보 안에 있습니다.</p>
        </div>
        {sourceError?.state === "error" && <ReadState error={sourceError.error} />}
        {sources.length === 0 && !sourceError ? <p className="empty">표시할 출처 기록이 없습니다.</p> : (
          <div className="source-grid profile-source-list">
            {sources.map((source) => (
              <article className="source" id={`source-${source.id}`} key={source.id}>
                <div className="source-card-topline"><span className="micro-label">출처 기록</span><span className="source-arrow" aria-hidden="true">↗</span></div>
                <h3><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></h3>
                <p className="source-meta">{source.publisher} <span>·</span> {source.source_class}</p>
                <p className="source-license">라이선스: {source.license ?? "라이선스 명시 없음"}</p>
                <dl className="policy-summary profile-policy">
                  <div><dt>수집</dt><dd>{source.policy_summary.collection}</dd></div>
                  <div><dt>메타데이터 저장</dt><dd>{source.policy_summary.metadata_storage}</dd></div>
                  <div><dt>원문 저장</dt><dd>{source.policy_summary.fulltext_storage}</dd></div>
                  <div><dt>발췌 표시</dt><dd>{source.policy_summary.excerpt_display}</dd></div>
                </dl>
                <details className="audit-details">
                  <summary>출처 감사 정보</summary>
                  <small>Source {source.id}<br />URL {source.url}<br />약관 확인일 {source.terms_checked_at ?? "기록 없음"}</small>
                </details>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
