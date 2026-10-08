"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useQueryState } from "./query-param";

import type { Person, PeopleDiscovery } from "../types";

// A source-listed 국감 witness row: text only, never a Person.
export type WitnessListing = {
  claimId: string;
  name: string;
  affiliationTitle: string | null;
  committeeName: string;
  category: string;
  attendanceDateText: string | null;
  sourceTag: string;
  officiallyPublished: boolean;
};

const FACETS = [
  ["party", "정당"],
  ["district", "지역구"],
  ["committees", "위원회"],
  ["reelection", "초선/재선"],
] as const;

type FilterKey = (typeof FACETS)[number][0];

export function discoveryFacetValues(discovery: PeopleDiscovery | undefined, key: FilterKey): string[] {
  const value = discovery?.facets[key]?.value;
  if (!value) return [];
  // Match the canonical ASSEMBLY_COMMITTEES delimiter (governance_ontology.py):
  // trim comma-separated official names, preserve their spelling, never fuzzy-match.
  return key === "committees"
    ? [...new Set(value.split(",").map((name) => name.trim()).filter(Boolean))]
    : [value];
}

export function matchesRosterFacets(discovery: PeopleDiscovery | undefined, filters: Partial<Record<FilterKey, string>>): boolean {
  return FACETS.every(([key]) => !filters[key] || discoveryFacetValues(discovery, key).includes(filters[key]!));
}

export default function RosterGrid({
  people,
  initialQuery = "",
  witnesses = [],
}: {
  people: Person[];
  initialQuery?: string;
  witnesses?: WitnessListing[];
}) {
  const [query, setQuery] = useQueryState(initialQuery);
  const [filters, setFilters] = useState<Partial<Record<FilterKey, string>>>({});
  const searchTerm = query.trim().toLocaleLowerCase();
  const facetOptions = useMemo(
    () => FACETS.map(([key, label]) => ({
      key,
      label,
      options: Array.from(new Set(
        people
          .flatMap((person) => discoveryFacetValues(person.discovery, key)),
      )).sort((left, right) => left.localeCompare(right, "ko")),
    })),
    [people],
  );
  const visiblePeople = useMemo(
    () => people.filter((person) => {
      const nameMatches = !searchTerm
        || person.canonical_name.toLocaleLowerCase().includes(searchTerm);
      const facetsMatch = matchesRosterFacets(person.discovery, filters);
      return nameMatches && facetsMatch;
    }),
    [filters, people, searchTerm],
  );
  const compactTerm = searchTerm.replace(/\s+/g, "");
  const witnessMatches = useMemo(
    () => compactTerm
      ? witnesses.filter((row) => row.name.toLocaleLowerCase().replace(/\s+/g, "").includes(compactTerm))
      : [],
    [compactTerm, witnesses],
  );
  const hasActiveFilters = Boolean(searchTerm || Object.values(filters).some(Boolean));
  const sameNameCounts = useMemo(() => people.reduce((counts, person) => {
    counts.set(person.canonical_name, (counts.get(person.canonical_name) ?? 0) + 1);
    return counts;
  }, new Map<string, number>()), [people]);

  function updateFilter(key: FilterKey, value: string) {
    setFilters((current) => ({ ...current, [key]: value || undefined }));
  }

  function clearFilters() {
    setQuery("");
    setFilters({});
  }

  return (
    <>
      <div className="roster-toolbar">
        <div>
          <p className="toolbar-count" role="status" aria-live="polite">
            <strong>{visiblePeople.length}명</strong>
            <span>표시 중 / 전체 {people.length}명</span>
          </p>
        </div>
        <label className="search-field">
          <span className="search-icon" aria-hidden="true">⌕</span>
          <span className="sr-only">이름으로 공개 기록 찾기</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="이름으로 찾기"
          />
        </label>
      </div>

      <fieldset className="directory-filters" aria-describedby="directory-filter-scope">
        <legend>국회 기본정보 필터</legend>
        {facetOptions.map(({ key, label, options }) => (
          <label className="filter-field" key={key}>
            <span>{label}</span>
            <select
              id={`filter-${key}`}
              aria-label={`${label} 필터`}
              disabled={options.length === 0}
              value={filters[key] ?? ""}
              onChange={(event) => updateFilter(key, event.target.value)}
            >
              <option value="">{options.length > 0 ? `전체 ${label}` : `공개된 ${label} 필터값 없음`}</option>
              {options.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
        ))}
        {hasActiveFilters && <button className="clear-filters" type="button" onClick={clearFilters}>필터 초기화</button>}
      </fieldset>
      <p className="directory-filter-scope" id="directory-filter-scope">
        필터는 공개된 국회 기본정보가 있는 인물에 적용됩니다. 이름 검색은 전체 인물을 대상으로 합니다.
      </p>

      {visiblePeople.length === 0 ? (
        <div className="empty-state">
          <div>
            <strong>{people.length === 0 ? "현재 공개 기록이 없습니다." : "일치하는 인물 기록이 없습니다."}</strong>
            <p>{people.length === 0 ? "현재 공개 조건에서 표시할 사람이 없습니다." : "이름이나 선택한 국회 기본정보 조건을 바꿔 보세요."}</p>
            {people.length > 0 && hasActiveFilters && <button className="clear-filters" type="button" onClick={clearFilters}>필터 초기화</button>}
          </div>
        </div>
      ) : (
        <div className="roster-list">
          {visiblePeople.map((person) => {
            const facets = person.discovery?.facets;
            const sameNameCount = sameNameCounts.get(person.canonical_name) ?? 1;
            const role = facets?.role?.value;
            const party = facets?.party?.value;
            const district = facets?.district?.value;
            const committees = facets?.committees?.value;
            const reelection = facets?.reelection?.value;
            const differentiators = [role, party, district, committees, reelection].filter(Boolean).join(" · ");
            return (
              <Link
                className="roster-row"
                href={`/people/${person.id}`}
                key={person.id}
                aria-label={`${person.canonical_name}${differentiators ? ` · ${differentiators}` : ""} · 인물 기록`}
              >
                <span className="row-main">
                  <span className="row-name-line">
                    <h3>{person.canonical_name}</h3>
                    {sameNameCount > 1 && <span className="same-name-note">동명이인 · {sameNameCount}명</span>}
                  </span>
                  {differentiators && <span className="row-role">{differentiators}</span>}
                </span>
                <span className="row-proof">{person.discovery?.evidence_ids.length
                  ? `국회 기본정보 근거 ${person.discovery.evidence_ids.length}개${person.discovery.as_of ? ` · 기준일 ${person.discovery.as_of}` : ""}`
                  : "프로필의 공개 기록 보기"}</span>
              </Link>
            );
          })}
        </div>
      )}
      {witnessMatches.length > 0 && (
        <section className="witness-matches" aria-labelledby="witness-matches-title">
          <h3 id="witness-matches-title">국감 공식 증인·참고인 명단 기재 {witnessMatches.length}건</h3>
          <p>공식 명단에 적힌 이름이며, 위 인물과 같은 사람인지는 확인하지 않았습니다. 출석 요구 명단이며 위법 판단이 아닙니다.</p>
          <ul>
            {witnessMatches.map((row) => (
              <li key={row.claimId}>
                <a href={`/gukgam/2026#witness-${row.claimId}`}>
                  <strong>{row.name}</strong>
                  <span>{row.affiliationTitle ?? "소속·직위 미기재"}</span>
                  <small>{row.committeeName} · {row.category}{row.attendanceDateText ? ` · 출석 ${row.attendanceDateText}` : ""} · {row.sourceTag}{row.officiallyPublished ? "" : " · 아직 공식 발표 아님"}</small>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
