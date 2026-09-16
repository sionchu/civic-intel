"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { Person, PeopleDiscovery } from "../types";

const FACETS = [
  ["party", "정당"],
  ["district", "지역구"],
  ["committees", "위원회"],
  ["reelection", "초선/재선"],
] as const;

type FilterKey = (typeof FACETS)[number][0];

function facetValue(discovery: PeopleDiscovery | undefined, key: FilterKey): string | null {
  return discovery?.facets[key]?.value ?? null;
}

export default function RosterGrid({ people }: { people: Person[] }) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Partial<Record<FilterKey, string>>>({});
  const searchTerm = query.trim().toLocaleLowerCase();
  const facetOptions = useMemo(
    () => FACETS.map(([key, label]) => ({
      key,
      label,
      options: Array.from(new Set(
        people
          .map((person) => facetValue(person.discovery, key))
          .filter((value): value is string => Boolean(value)),
      )).sort((left, right) => left.localeCompare(right, "ko")),
    })).filter((facet) => facet.options.length > 0),
    [people],
  );
  const visiblePeople = useMemo(
    () => people.filter((person) => {
      const nameMatches = !searchTerm
        || person.canonical_name.toLocaleLowerCase().includes(searchTerm);
      const facetsMatch = FACETS.every(([key]) => {
        const selected = filters[key];
        return !selected || facetValue(person.discovery, key) === selected;
      });
      return nameMatches && facetsMatch;
    }),
    [filters, people, searchTerm],
  );
  const hasActiveFilters = Boolean(searchTerm || Object.values(filters).some(Boolean));
  const incompletePeople = people.filter((person) => (
    (person.discovery?.missing_fields.length ?? 0) > 0
      || (person.discovery?.ambiguous_fields.length ?? 0) > 0
  )).length;
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
          <span className="micro-label">People directory</span>
          <p className="toolbar-count">
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

      {facetOptions.length > 0 && (
        <div className="directory-filters" aria-label="공개 기본 프로필 필터">
          {facetOptions.map(({ key, label, options }) => (
            <label className="filter-field" key={key}>
              <span>{label}</span>
              <select
                aria-label={`${label} 필터`}
                value={filters[key] ?? ""}
                onChange={(event) => updateFilter(key, event.target.value)}
              >
                <option value="">전체 {label}</option>
                {options.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
          ))}
          {hasActiveFilters && <button className="clear-filters" type="button" onClick={clearFilters}>필터 초기화</button>}
        </div>
      )}

      {incompletePeople > 0 && (
        <p className="incomplete-note" role="status">
          {incompletePeople}개 profile은 일부 공개 기본 프로필 Claim이 없어 해당 필터에서 제외될 수 있습니다. 빈 값은 추론하지 않습니다.
        </p>
      )}

      {visiblePeople.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">∅</span>
          <div>
            <strong>{people.length === 0 ? "현재 공개 기록이 없습니다." : "검색 결과가 없습니다."}</strong>
            <p>{people.length === 0 ? "현재 공개 조건에서 표시할 사람이 없습니다." : "표시된 이름과 공개 Claim 값으로만 검색합니다."}</p>
            {people.length > 0 && hasActiveFilters && <button className="clear-filters" type="button" onClick={clearFilters}>필터 초기화</button>}
          </div>
        </div>
      ) : (
        <div className="roster-list">
          {visiblePeople.map((person, index) => {
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
                aria-label={`${person.canonical_name}${differentiators ? ` · ${differentiators}` : ""} · Evidence profile`}
              >
                <span className="row-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <span className="row-avatar" aria-hidden="true">{person.canonical_name.trim().slice(0, 1)}</span>
                <span className="row-main">
                  <span className="row-name-line">
                    <h3>{person.canonical_name}</h3>
                    {sameNameCount > 1 && <span className="same-name-note">동명이인 · {sameNameCount}명</span>}
                  </span>
                  <span className="row-role">{role ?? "역할 정보 없음"}</span>
                </span>
                <span className="row-facts">
                  <span><small>정당</small><strong>{party ?? "공개 정보 없음"}</strong></span>
                  <span><small>지역구</small><strong>{district ?? "공개 정보 없음"}</strong></span>
                </span>
                <span className="row-secondary">
                  <span><small>위원회</small><strong>{committees ?? "공개 정보 없음"}</strong></span>
                  <span><small>초선/재선</small><strong>{reelection ?? "공개 정보 없음"}</strong></span>
                </span>
                <span className="row-proof">근거 {person.discovery?.evidence_ids.length ?? 0}개 · 기준일 {person.discovery?.as_of ?? "정보 없음"}</span>
                <span className="row-arrow" aria-hidden="true">↗</span>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
