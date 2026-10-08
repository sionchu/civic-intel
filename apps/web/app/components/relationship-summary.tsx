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

const unique = (values: string[]) => [...new Set(values)];
const PREVIEW_NAMES = 12;
const PREVIEW_CLAIMS = 20;

// Compact on purpose: every person page is a static file under the Sites bundle cap, so a group
// shows its relation types, rules, timing basis and the first names; per-relation detail stays in
// the API and on each counterpart's own page.
export default function RelationshipSummary({ limitations, groups, cosponsors }: RelationshipSummaryProps) {
  return (
    <>
      <ul className="relationship-limitations">{limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
      {groups.map((group, index) => {
        const relations = group.publicOthers.flatMap((item) => item.relations);
        const types = unique(relations.map((relation) => RELATION_TYPES[relation.type] ?? relation.type));
        const rules = unique(relations.map((relation) => relation.rule));
        const overlaps = unique(relations.map((relation) => OVERLAP[relation.overlap] ?? relation.overlap));
        const claimIds = unique(relations.flatMap((relation) => relation.claimIds));
        const preview = group.publicOthers.slice(0, PREVIEW_NAMES);
        const hiddenNames = group.publicOthers.length - preview.length;
        return (
          <div className="relationship-group" key={`${group.label}-${group.layer}-${index}`}>
            <h3>{group.label} <span>· {group.layer}</span></h3>
            <p className="relationship-count">
              반환된 관계 {group.returnedRelations.toLocaleString("ko-KR")}건
              {group.totalRelations > group.returnedRelations && ` / 전체 ${group.totalRelations.toLocaleString("ko-KR")}건`}
              {` · 다른 사람 ${group.distinctOthers.toLocaleString("ko-KR")}명(공개 인물 ${group.publicOthers.length.toLocaleString("ko-KR")}명)`}
            </p>
            {types.length > 0 && <p className="relationship-count">{types.join(" · ")} · DERIVED · {rules.join(", ")} · {overlaps.join(" · ")}</p>}
            <ul className="relationship-names">{preview.map((item) => (
              <li key={item.id}><Link href={`/people/${item.id}`}>{item.name}</Link></li>
            ))}{hiddenNames > 0 && <li>외 {hiddenNames.toLocaleString("ko-KR")}명</li>}</ul>
            {claimIds.length > 0 && (
              <details className="audit-details">
                <summary>근거 Claim {claimIds.length.toLocaleString("ko-KR")}개{claimIds.length > PREVIEW_CLAIMS ? ` 중 ${PREVIEW_CLAIMS}개` : ""}</summary>
                <small>{claimIds.slice(0, PREVIEW_CLAIMS).join(", ")}</small>
              </details>
            )}
            {group.totalRelations > group.returnedRelations && (
              <p className="relationship-count">관계 API가 그룹당 최대 300건을 반환해 전체 명단은 이 화면에 없습니다.</p>
            )}
          </div>
        );
      })}
      {cosponsors.length > 0 && (
        <div className="relationship-group">
          <h3>공동발의</h3>
          <p className="relationship-count">공개 인물 중 공동발의가 많은 상위 {cosponsors.length}명 · {unique(cosponsors.map((item) => item.type)).join(", ")} · DERIVED · {unique(cosponsors.map((item) => item.rule)).join(", ")}</p>
          <ol className="relationship-cosponsors">{cosponsors.map((item) => (
            <li key={item.id}>
              <Link href={`/people/${item.id}`}>{item.name}</Link>
              <span>공동발의 {item.bills.toLocaleString("ko-KR")}건</span>
            </li>
          ))}</ol>
        </div>
      )}
    </>
  );
}
