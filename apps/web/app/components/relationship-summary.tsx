import Link from "next/link";

import type { Person, PersonRelationships } from "../types";

type Relation = {
  type: string;
  status: "DERIVED";
  rule: string;
  overlap: string;
  basis: string;
  ownPeriod: string;
  otherPeriod: string;
  claimIds: string[];
  evidenceIds: string[];
  sourceIds: string[];
};

type Counterpart = { id: string; name: string; relations: Relation[] };
type Group = {
  label: string;
  layer: string;
  returnedRelations: number;
  totalRelations: number;
  distinctOthers: number;
  publicOthers: Counterpart[];
};
type Cosponsor = { id: string; name: string; bills: number; type: string; rule: string; claimIds: string[] };

export type RelationshipSummaryProps = {
  limitations: string[];
  groups: Group[];
  cosponsors: Cosponsor[];
};

const LAYERS: Record<string, string> = {
  POLITICAL: "정당", LEGISLATIVE: "입법", PUBLIC_INSTITUTION: "공공기관",
  BUSINESS: "기업", OVERSIGHT: "국정감사", EDUCATION: "교육",
  CAREER: "경력", CAMPAIGN: "선거", GOVERNMENT: "정부",
};

const OVERLAP: Record<string, string> = {
  VERIFIED: "같은 시점 확인", NOT_OVERLAPPING: "기간 겹치지 않음", UNKNOWN: "시점 미확인",
};

const RELATION_TYPES: Record<string, string> = {
  SAME_PARLIAMENTARY_COMMITTEE: "같은 상임위원회", SAME_SPECIAL_COMMITTEE: "같은 특별위원회",
  SAME_PARTY: "같은 정당", SAME_PUBLIC_INSTITUTION: "같은 공공기관",
  PUBLIC_INSTITUTION_OVERLAP: "공공기관 재직 기간 겹침",
  SAME_COMPANY_BOARD: "같은 기업 임원 명단", BOARD_INTERLOCK: "기업 임원 기간 겹침",
  COMMITTEE_WITNESS_REQUEST: "위원회 명단 관계", SAME_UNIVERSITY: "같은 대학교",
  SAME_GRADUATE_SCHOOL: "같은 대학원", SAME_DEPARTMENT: "같은 학과",
  SAME_HIGH_SCHOOL: "같은 고등학교", EDUCATION_TIME_OVERLAP: "교육 기간 겹침",
  SAME_GOVERNMENT_BODY: "같은 정부기관", GOVERNMENT_OVERLAP: "정부기관 재직 기간 겹침",
  SAME_CAMPAIGN: "같은 선거운동 조직", SAME_TRANSITION_COMMITTEE: "같은 인수위원회",
  SAME_GOVERNMENT_COMMITTEE: "같은 정부위원회", SAME_EMPLOYER: "같은 경력 기관",
  EMPLOYMENT_OVERLAP: "경력 기간 겹침",
};

function period(value: { start: string | null; end: string | null; as_of: string | null }): string {
  if (value.start || value.end) return `${value.start ?? "시작 미기재"} ~ ${value.end ?? "종료 미기재"}`;
  return value.as_of ? `기준일 ${value.as_of}` : "시점 미기재";
}

export function summarizeRelationships(
  personId: string,
  payload: PersonRelationships,
  people: Person[],
): RelationshipSummaryProps {
  const publicNames = new Map(people.filter((person) => person.identity_status === "RESOLVED")
    .map((person) => [person.id, person.canonical_name]));
  const groups = payload.groups.flatMap((group) => {
    const derived = group.relations.filter((relation) => relation.status === "DERIVED");
    if (derived.length === 0) return [];
    const others = new Map<string, Counterpart>();
    const distinct = new Set<string>();
    for (const relation of derived) {
      const otherId = relation.subject_person_id === personId
        ? relation.object_person_id : relation.subject_person_id;
      if (otherId === personId) continue;
      distinct.add(otherId);
      const name = publicNames.get(otherId);
      if (!name) continue;
      let counterpart = others.get(otherId);
      if (!counterpart) {
        counterpart = { id: otherId, name, relations: [] };
        others.set(otherId, counterpart);
      }
      counterpart.relations.push({
        type: relation.relation_type,
        status: "DERIVED",
        rule: `${relation.rule_id}@${relation.rule_version}`,
        overlap: relation.temporal.overlap,
        basis: relation.temporal.basis,
        ownPeriod: period(relation.subject_person_id === personId
          ? relation.temporal.subject_period : relation.temporal.object_period),
        otherPeriod: period(relation.subject_person_id === personId
          ? relation.temporal.object_period : relation.temporal.subject_period),
        claimIds: relation.source_claim_ids,
        evidenceIds: relation.evidence_ids,
        sourceIds: relation.source_ids,
      });
    }
    return [{
      label: group.via.label,
      layer: LAYERS[group.layer] ?? group.layer,
      returnedRelations: derived.length,
      totalRelations: derived.length === group.relations.length ? group.relation_count : derived.length,
      distinctOthers: distinct.size,
      publicOthers: [...others.values()].sort((left, right) => left.name.localeCompare(right.name, "ko")),
    }];
  });
  const cosponsors = payload.cosponsorship.filter((item) => item.status === "DERIVED")
    .map((item) => {
      const id = item.subject_person_id === personId ? item.object_person_id : item.subject_person_id;
      const name = publicNames.get(id);
      return name ? { id, name, bills: item.shared_bill_count, type: item.relation_type,
        rule: `${item.rule_id}@${item.rule_version}`, claimIds: item.source_claim_ids } : null;
    })
    .filter((item): item is Cosponsor => item !== null)
    .sort((left, right) => right.bills - left.bills || left.name.localeCompare(right.name, "ko"))
    .slice(0, 10);
  return { limitations: payload.limitations, groups, cosponsors };
}

function RelationDetail({ relation }: { relation: Relation }) {
  return (
    <li className="relationship-relation">
      <span>{RELATION_TYPES[relation.type] ?? relation.type}</span>
      <small>{relation.type} · DERIVED · {relation.rule}</small>
      <small>{OVERLAP[relation.overlap] ?? relation.overlap} · {relation.basis}</small>
      <small>본인 {relation.ownPeriod} · 상대 {relation.otherPeriod}</small>
      <details className="audit-details">
        <summary>Claim·Evidence·Source</summary>
        <small>Claim {relation.claimIds.join(", ") || "없음"}</small>
        <small>Evidence {relation.evidenceIds.join(", ") || "없음"}</small>
        <small>Source {relation.sourceIds.map((id, index) => (
          <span key={id}>{index > 0 ? ", " : ""}<a href={`#source-${id}`}>{id}</a></span>
        ))}</small>
      </details>
    </li>
  );
}

function CounterpartRow({ item }: { item: Counterpart }) {
  return (
    <li className="relationship-person">
      <Link href={`/people/${item.id}`}>{item.name}</Link>
      <ul>{item.relations.map((relation, index) => <RelationDetail key={`${item.id}-${index}`} relation={relation} />)}</ul>
    </li>
  );
}

export default function RelationshipSummary({ limitations, groups, cosponsors }: RelationshipSummaryProps) {
  return (
    <>
      <ul className="relationship-limitations">{limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
      {groups.map((group, index) => {
        const preview = group.publicOthers.slice(0, 12);
        const remaining = group.publicOthers.slice(12);
        return (
          <div className="relationship-group" key={`${group.label}-${group.layer}-${index}`}>
            <h3>{group.label} <span>· {group.layer}</span></h3>
            <p className="relationship-count">
              반환된 관계 {group.returnedRelations.toLocaleString("ko-KR")}건
              {group.totalRelations > group.returnedRelations && ` / 전체 ${group.totalRelations.toLocaleString("ko-KR")}건`}
              {` · 확인된 다른 사람 ${group.distinctOthers.toLocaleString("ko-KR")}명`}
              {` · 공개 명단 이름 ${group.publicOthers.length.toLocaleString("ko-KR")}명 중 ${preview.length}명 표시`}
            </p>
            <ul className="relationship-people">{preview.map((item) => <CounterpartRow key={item.id} item={item} />)}</ul>
            {remaining.length > 0 && (
              <details className="relationship-more">
                <summary>나머지 공개 명단 {remaining.length.toLocaleString("ko-KR")}명 보기</summary>
                {/* Names only: per-relation audit details stay on the 12 shown above and on each
                    person's own page, keeping static pages within the Sites bundle cap. */}
                <ul className="relationship-names">{remaining.map((item) => (
                  <li key={item.id}><Link href={`/people/${item.id}`}>{item.name}</Link></li>
                ))}</ul>
              </details>
            )}
            {group.totalRelations > group.returnedRelations && (
              <p className="relationship-count">API의 그룹당 최대 300건 제한으로 전체 관계 명단은 이 응답에서 확인할 수 없습니다.</p>
            )}
          </div>
        );
      })}
      {cosponsors.length > 0 && (
        <div className="relationship-group">
          <h3>공동발의</h3>
          <p className="relationship-count">공개 명단에서 확인된 상위 {cosponsors.length}명</p>
          <ol className="relationship-cosponsors">{cosponsors.map((item) => (
            <li key={item.id}>
              <Link href={`/people/${item.id}`}>{item.name}</Link>
              <span>공동발의 {item.bills.toLocaleString("ko-KR")}건</span>
              <small>{item.type} · DERIVED · {item.rule}</small>
              <details className="audit-details"><summary>근거 Claim</summary><small>{item.claimIds.join(", ")}</small></details>
            </li>
          ))}</ol>
        </div>
      )}
    </>
  );
}
