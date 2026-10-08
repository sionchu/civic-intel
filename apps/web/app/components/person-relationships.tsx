import Link from "next/link";

import { statedDate } from "../career-period";
import type { PersonRelationships, RelationshipPeriod } from "../types";

const LABELS: Record<string, string> = {
  SAME_PARLIAMENTARY_COMMITTEE: "같은 상임위원회", SAME_SPECIAL_COMMITTEE: "같은 특별위원회",
  SAME_PARTY: "같은 정당 기록", SAME_LEGISLATIVE_TERM: "같은 국회 임기",
  SAME_PUBLIC_INSTITUTION: "같은 공공기관 기록", PUBLIC_INSTITUTION_OVERLAP: "공공기관 소속 기간 겹침",
  SAME_COMPANY_BOARD: "같은 기업 임원 공시", BOARD_INTERLOCK: "기업 임원 공시 기간 겹침",
  COMMITTEE_WITNESS_REQUEST: "위원회 위원·출석 요구 관계",
  SAME_UNIVERSITY: "같은 대학교 기록", SAME_GRADUATE_SCHOOL: "같은 대학원 기록",
  SAME_DEPARTMENT: "같은 학과 기록", SAME_HIGH_SCHOOL: "같은 고등학교 기록",
  EDUCATION_TIME_OVERLAP: "교육 기간 겹침", SAME_GOVERNMENT_BODY: "같은 정부기관 기록",
  GOVERNMENT_OVERLAP: "정부기관 소속 기간 겹침", SAME_CAMPAIGN: "같은 선거 캠프 기록",
  SAME_TRANSITION_COMMITTEE: "같은 인수위원회 기록", SAME_GOVERNMENT_COMMITTEE: "같은 정부위원회 기록",
  SAME_EMPLOYER: "같은 기관 경력", EMPLOYMENT_OVERLAP: "경력 기간 겹침",
  SAME_CAMPAIGN_OVERLAP: "선거 캠프 기간 겹침", SAME_TRANSITION_COMMITTEE_OVERLAP: "인수위원회 기간 겹침",
  SAME_GOVERNMENT_COMMITTEE_OVERLAP: "정부위원회 기간 겹침",
  BILL_COSPONSORSHIP: "공동 법안 발의", REPEATED_COSPONSORSHIP: "복수 법안 공동 발의",
};

const OVERLAP = { VERIFIED: "시간 겹침 확인", UNKNOWN: "시간 겹침 미확인", NOT_OVERLAPPING: "확인된 기간은 겹치지 않음" };

function periodText(period: RelationshipPeriod): string {
  // The API returns conservative overlap bounds, not each endpoint's source precision.
  // Never use its single start precision to label an independently coarser end date.
  const start = statedDate(period.start, "DAY");
  const end = statedDate(period.end, "DAY");
  if (start || end) return `비교 경계 ${start ?? "시작 미기재"} – ${end ?? "종료 미기재"}`;
  return period.as_of ? `자료 기준 ${period.as_of}` : "기간 미기재";
}

export default function PersonRelationshipsView({ data }: { data: PersonRelationships }) {
  const shown = data.groups.reduce((count, group) => count + group.relations.length, 0);
  return (
    <div className="relationship-records">
      <h3>공식 기록이 교차하는 인물</h3>
      <p className="section-note">같은 기관·위원회·공적 활동 기록을 비교한 연결입니다. 친분·영향력을 뜻하지 않습니다.</p>
      <p className="section-note">비교 경계는 기간 겹침 계산에 쓰인 보수적인 날짜입니다. 원문 기간과 정밀도는 양쪽 근거 기록에서 확인합니다.</p>
      {shown === 0 ? (
        <p className="empty" role="status">현재 공개 기록에서 표시할 인물 간 연결이 없습니다.</p>
      ) : data.groups.map((group) => (
        <section className="relationship-group" key={group.via.key}>
          <h4>{group.via.organization_id ? <Link href={`/organizations/${group.via.organization_id}`}>{group.via.label}</Link> : group.via.label}</h4>
          <p className="section-note">공개 연결 {group.relation_count}건 중 {group.relations.length}건 표시 · 접점별 최대 3건</p>
          <ul className="relationship-list">
            {group.relations.map((relation) => {
              const subjectIsCurrent = relation.subject_person_id === data.person.id;
              const currentPeriod = subjectIsCurrent ? relation.temporal.subject_period : relation.temporal.object_period;
              const otherPeriod = subjectIsCurrent ? relation.temporal.object_period : relation.temporal.subject_period;
              return (
                <li key={relation.relation_id} className="relationship-record">
                  <div className="relationship-heading">
                    <Link href={`/people/${relation.counterpart.id}`}>{relation.counterpart.name}</Link>
                    <span className="status DERIVED">{relation.status}</span>
                  </div>
                  <p>{LABELS[relation.relation_type] ?? "공식 기록상 접점"} · {OVERLAP[relation.temporal.overlap]}</p>
                  <dl className="relationship-periods">
                    <div><dt>{data.person.name}</dt><dd>{periodText(currentPeriod)}</dd></div>
                    <div><dt>{relation.counterpart.name}</dt><dd>{periodText(otherPeriod)}</dd></div>
                  </dl>
                  {relation.source_conflict && <p><span className="status CONFLICT">SOURCE CONFLICT</span> 연결에 사용한 근거가 상충합니다.</p>}
                  <details className="relationship-evidence">
                    <summary>양쪽 기록과 원문 근거</summary>
                    <ul>
                      {relation.source_claim_ids.map((claimId, index) => {
                        const personId = index === 0 ? relation.subject_person_id : relation.object_person_id;
                        return <li key={claimId}><Link href={personId === data.person.id ? `#claim-${claimId}` : `/people/${personId}#claim-${claimId}`}>{personId === data.person.id ? data.person.name : relation.counterpart.name}의 근거 기록</Link></li>;
                      })}
                      {relation.source_ids.map((sourceId) => <li key={sourceId}><a href={`#source-${sourceId}`}>원문 출처</a></li>)}
                    </ul>
                    <p>{relation.interpretation_note}</p>
                    <small>규칙 {relation.rule_id} · {relation.rule_version} / 시간 근거 {relation.temporal.basis}</small>
                    <details className="audit-details"><summary>근거 식별자</summary><p>{relation.evidence_ids.join(" · ")}</p></details>
                  </details>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
      <details className="relationship-method">
        <summary>연결의 범위와 방법 · 규칙 {data.ruleset_version}</summary>
        <p>표시 {shown}건 / 현재 공개 입력에서 계산된 연결 {data.relation_count}건. 표시 순서는 중요도나 영향력 순위가 아닙니다.</p>
        <ul>{data.limitations.map((note) => <li key={note}>{note}</li>)}</ul>
      </details>
    </div>
  );
}
