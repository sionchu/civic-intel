"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { Person } from "../types";

export default function RosterGrid({ people }: { people: Person[] }) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visiblePeople = useMemo(
    () =>
      normalizedQuery
        ? people.filter((person) => person.canonical_name.toLocaleLowerCase().includes(normalizedQuery))
        : people,
    [normalizedQuery, people],
  );

  return (
    <>
      <div className="roster-toolbar">
        <div>
          <span className="micro-label">Resolved identities</span>
          <p className="toolbar-count">
            <strong>{visiblePeople.length}</strong>
            <span>of {people.length} profiles</span>
          </p>
        </div>
        <label className="search-field">
          <span className="search-icon" aria-hidden="true">⌕</span>
          <span className="sr-only">이름으로 공개 roster 필터링</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="이름으로 찾기"
          />
        </label>
      </div>

      {visiblePeople.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">∅</span>
          <div>
            <strong>{people.length === 0 ? "Resolved identities are not available." : "검색 결과가 없습니다."}</strong>
            <p>{people.length === 0 ? "The public roster will appear when the API is available." : "표시된 canonical 이름으로만 검색합니다."}</p>
          </div>
        </div>
      ) : (
        <div className="roster-grid">
          {visiblePeople.map((person, index) => (
            <Link className="person-card" href={`/people/${person.id}`} key={person.id}>
              <div className="card-topline">
                <span className="card-number">{String(index + 1).padStart(2, "0")}</span>
                <span className="status RESOLVED">RESOLVED</span>
              </div>
              <span className="person-avatar" aria-hidden="true">
                {person.canonical_name.slice(0, 1)}
              </span>
              <h3>{person.canonical_name}</h3>
              <div className="card-footer">
                <span>Evidence profile</span>
                <span className="card-arrow" aria-hidden="true">↗</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
