"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { OrganizationSummary, Person } from "../types";

export type GukgamSearchPerson = Pick<
  Person,
  "id" | "canonical_name" | "discovery"
>;

function normalizeSearchValue(value: string): string {
  return value.toLocaleLowerCase("ko-KR").replace(/\s+/g, "");
}

function personSearchValue(person: GukgamSearchPerson): string {
  const facets = person.discovery?.facets;
  return normalizeSearchValue(
    [
      person.canonical_name,
      facets?.role?.value,
      facets?.party?.value,
      facets?.district?.value,
      facets?.committees?.value,
      facets?.reelection?.value,
    ]
      .filter((value): value is string => Boolean(value))
      .join(" "),
  );
}

function organizationSearchValue(organization: OrganizationSummary): string {
  return normalizeSearchValue(
    [organization.name, organization.classification, organization.classification_code]
      .filter((value): value is string => Boolean(value))
      .join(" "),
  );
}

export default function GukgamSearch({
  initialQuery,
  people,
  organizations,
}: {
  initialQuery: string;
  people: GukgamSearchPerson[];
  organizations: OrganizationSummary[];
}) {
  const [query, setQuery] = useState(initialQuery);

  function updateQuery(nextQuery: string): void {
    setQuery(nextQuery);
    const url = new URL(window.location.href);
    const trimmed = nextQuery.trim();
    if (trimmed) {
      url.searchParams.set("q", trimmed.slice(0, 80));
    } else {
      url.searchParams.delete("q");
    }
    window.history.replaceState(
      window.history.state,
      "",
      url.pathname + url.search + url.hash,
    );
  }
  const normalizedQuery = normalizeSearchValue(query.trim());

  const sameNameCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const person of people) {
      counts.set(person.canonical_name, (counts.get(person.canonical_name) ?? 0) + 1);
    }
    return counts;
  }, [people]);

  const peopleResults = useMemo(
    () =>
      normalizedQuery
        ? people
            .filter((person) => personSearchValue(person).includes(normalizedQuery))
            .slice(0, 6)
        : [],
    [normalizedQuery, people],
  );

  const organizationResults = useMemo(
    () =>
      normalizedQuery
        ? organizations
            .filter((organization) =>
              organizationSearchValue(organization).includes(normalizedQuery),
            )
            .slice(0, 6)
        : [],
    [normalizedQuery, organizations],
  );

  const resultCount = peopleResults.length + organizationResults.length;

  return (
    <section className="gukgam-search" aria-labelledby="gukgam-search-title">
      <div className="gukgam-search-heading">
        <div>
          <span className="eyebrow">Search / current public records</span>
          <h2 id="gukgam-search-title">인물과 기관에서 시작</h2>
        </div>
        <p>
          이름, 공개된 역할·정당·지역구·위원회 또는 기관명으로 현재 Civic Intel 기록을
          좁혀보세요. 검색은 표시 대상을 필터링할 뿐 새로운 identity 연결을 만들지 않습니다.
        </p>
      </div>

      <label className="gukgam-search-field">
        <span className="sr-only">국감 2026 인물 및 기관 검색</span>
        <span className="search-icon" aria-hidden="true">⌕</span>
        <input
          type="search"
          value={query}
          onChange={(event) => updateQuery(event.target.value)}
          placeholder="예: 안철수, 한국전력공사, 법제사법위원회"
          autoComplete="off"
          maxLength={80}
        />
      </label>
      {normalizedQuery && (
        <p className="gukgam-search-share-note">
          현재 검색어가 주소에 반영됩니다. 이 URL을 그대로 공유할 수 있습니다.
        </p>
      )}

      {!normalizedQuery ? (
        <div className="gukgam-search-idle" role="status">
          <strong>검색어를 입력하세요.</strong>
          <span>
            현재 공개 범위: People {people.length}명 · Organizations {organizations.length}개
          </span>
        </div>
      ) : resultCount === 0 ? (
        <div className="gukgam-search-idle" role="status">
          <strong>현재 공개 기록에서 일치 항목이 없습니다.</strong>
          <span>기록이 없다는 뜻이 아니라 현재 공개·검색 가능한 범위의 결과가 비어 있습니다.</span>
        </div>
      ) : (
        <div className="gukgam-search-results" aria-live="polite">
          {peopleResults.length > 0 && (
            <div className="gukgam-search-group">
              <div className="gukgam-search-group-heading">
                <strong>People</strong>
                <span>{peopleResults.length}건 표시</span>
              </div>
              <div className="gukgam-search-list">
                {peopleResults.map((person) => {
                  const facets = person.discovery?.facets;
                  return (
                    <Link
                      className="gukgam-search-row"
                      href={"/people/" + person.id}
                      key={person.id}
                    >
                      <span className="gukgam-search-avatar" aria-hidden="true">
                        {person.canonical_name.trim().slice(0, 1)}
                      </span>
                      <span className="gukgam-search-row-main">
                        <span className="gukgam-search-name-line">
                          <strong>{person.canonical_name}</strong>
                          {(sameNameCounts.get(person.canonical_name) ?? 0) > 1 && (
                            <small>동명이인 기록 분리</small>
                          )}
                        </span>
                        <span>
                          {facets?.role?.value ?? "공개 역할 정보 없음"}
                          {facets?.party?.value ? " · " + facets.party.value : ""}
                        </span>
                      </span>
                      <span className="gukgam-search-context">
                        {facets?.district?.value ?? facets?.committees?.value ?? "추가 공개 정보 없음"}
                      </span>
                      <span className="row-arrow" aria-hidden="true">↗</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {organizationResults.length > 0 && (
            <div className="gukgam-search-group">
              <div className="gukgam-search-group-heading">
                <strong>Organizations</strong>
                <span>{organizationResults.length}건 표시</span>
              </div>
              <div className="gukgam-search-list">
                {organizationResults.map((organization) => (
                  <Link
                    className="gukgam-search-row"
                    href={"/organizations/" + organization.id}
                    key={organization.id}
                  >
                    <span className="gukgam-search-avatar organization" aria-hidden="true">
                      {organization.name.trim().slice(0, 1)}
                    </span>
                    <span className="gukgam-search-row-main">
                      <strong>{organization.name}</strong>
                      <span>{organization.classification ?? "분류 공개 정보 없음"}</span>
                    </span>
                    <span className="gukgam-search-context">
                      임원 {organization.executive_count}건 · Evidence {organization.evidence_count}개
                    </span>
                    <span className="row-arrow" aria-hidden="true">↗</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
