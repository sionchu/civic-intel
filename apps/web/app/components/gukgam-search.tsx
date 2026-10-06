"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useQueryState } from "./query-param";

import type { OrganizationSummary, Person } from "../types";

// Search receives only the displayed facet values (not evidence IDs) to keep the page light.
export type GukgamSearchFacets = {
  role: { value: string } | null;
  party: { value: string } | null;
  district: { value: string } | null;
  committees: { value: string } | null;
  reelection: { value: string } | null;
};

export type GukgamSearchPerson = Pick<Person, "id" | "canonical_name"> & {
  discovery?: { facets: GukgamSearchFacets };
};

const INITIAL_RESULT_LIMIT = 6;
const RESULT_PAGE_SIZE = 12;

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
  const [query, setQuery] = useQueryState(initialQuery);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [peopleLimit, setPeopleLimit] = useState(INITIAL_RESULT_LIMIT);
  const [organizationLimit, setOrganizationLimit] = useState(INITIAL_RESULT_LIMIT);

  function updateQuery(nextQuery: string): void {
    setQuery(nextQuery);
    setCopyStatus("idle");
    setPeopleLimit(INITIAL_RESULT_LIMIT);
    setOrganizationLimit(INITIAL_RESULT_LIMIT);
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
  async function copyShareUrl(): Promise<void> {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  const normalizedQuery = normalizeSearchValue(query.trim());

  const sameNameCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const person of people) {
      counts.set(person.canonical_name, (counts.get(person.canonical_name) ?? 0) + 1);
    }
    return counts;
  }, [people]);

  const peopleMatches = useMemo(
    () =>
      normalizedQuery
        ? people.filter((person) => personSearchValue(person).includes(normalizedQuery))
        : [],
    [normalizedQuery, people],
  );
  const peopleResults = peopleMatches.slice(0, peopleLimit);

  const organizationMatches = useMemo(
    () =>
      normalizedQuery
        ? organizations.filter((organization) =>
            organizationSearchValue(organization).includes(normalizedQuery),
          )
        : [],
    [normalizedQuery, organizations],
  );
  const organizationResults = organizationMatches.slice(0, organizationLimit);

  const resultCount = peopleMatches.length + organizationMatches.length;

  return (
    <section className="gukgam-search" aria-labelledby="gukgam-search-title">
      <div className="gukgam-search-heading">
        <h2 id="gukgam-search-title">인물·기관 검색</h2>
        <p>이름, 역할, 정당, 지역구, 위원회 또는 기관명으로 찾습니다. 검색은 보이는 기록을 거를 뿐 기록끼리 새로 연결하지 않습니다.</p>
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
        <div className="gukgam-search-share-row">
          <p className="gukgam-search-share-note">
            현재 검색어가 주소에 반영됩니다. 이 URL을 그대로 공유할 수 있습니다.
          </p>
          <button
            className="gukgam-search-copy"
            type="button"
            onClick={copyShareUrl}
          >
            {copyStatus === "copied" ? "복사됨" : "공유 링크 복사"}
          </button>
          <span className="sr-only" role="status" aria-live="polite">
            {copyStatus === "copied"
              ? "공유 링크를 클립보드에 복사했습니다."
              : copyStatus === "failed"
                ? "링크를 복사하지 못했습니다. 주소창의 URL을 직접 복사해주세요."
                : ""}
          </span>
        </div>
      )}

      {!normalizedQuery ? (
        <div className="gukgam-search-idle" role="status">
          <strong>검색어를 입력하세요.</strong>
          <span>
            현재 공개 범위: 인물 {people.length}명 · 기관 {organizations.length}개
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
                <strong>인물</strong>
                <span>{peopleResults.length} / {peopleMatches.length}건 표시</span>
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
                    </Link>
                  );
                })}
              </div>
              {peopleResults.length < peopleMatches.length && (
                <button
                  className="gukgam-search-more"
                  type="button"
                  onClick={() =>
                    setPeopleLimit((current) =>
                      Math.min(current + RESULT_PAGE_SIZE, peopleMatches.length),
                    )
                  }
                >
                  인물 {Math.min(RESULT_PAGE_SIZE, peopleMatches.length - peopleResults.length)}개 더 보기
                </button>
              )}
            </div>
          )}

          {organizationResults.length > 0 && (
            <div className="gukgam-search-group">
              <div className="gukgam-search-group-heading">
                <strong>기관</strong>
                <span>{organizationResults.length} / {organizationMatches.length}건 표시</span>
              </div>
              <div className="gukgam-search-list">
                {organizationResults.map((organization) => (
                  <Link
                    className="gukgam-search-row"
                    href={"/organizations/" + organization.id}
                    key={organization.id}
                  >
                    <span className="gukgam-search-row-main">
                      <strong>{organization.name}</strong>
                      <span>{organization.classification ?? "분류 공개 정보 없음"}</span>
                    </span>
                    <span className="gukgam-search-context">
                      임원 {organization.executive_count}건 · 근거 {organization.evidence_count}개
                    </span>
                  </Link>
                ))}
              </div>
              {organizationResults.length < organizationMatches.length && (
                <button
                  className="gukgam-search-more"
                  type="button"
                  onClick={() =>
                    setOrganizationLimit((current) =>
                      Math.min(current + RESULT_PAGE_SIZE, organizationMatches.length),
                    )
                  }
                >
                  기관 {Math.min(
                    RESULT_PAGE_SIZE,
                    organizationMatches.length - organizationResults.length,
                  )}개 더 보기
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
