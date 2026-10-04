"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { OrganizationSummary } from "../types";
import { DIRECTORY_PAGE_SIZE } from "./roster-grid";

const UNCLASSIFIED = "__unclassified__";

// Client-side filter over the already-public organization summaries. It narrows what is displayed;
// it never creates, merges or reorders organizations by importance. Order stays as served.
export default function OrganizationDirectory({ organizations }: { organizations: OrganizationSummary[] }) {
  const [query, setQuery] = useState("");
  const [classification, setClassification] = useState("");
  const [limit, setLimit] = useState(DIRECTORY_PAGE_SIZE);
  const term = query.trim().toLocaleLowerCase();
  const classifications = useMemo(
    () => Array.from(new Set(organizations.map((item) => item.classification).filter((value): value is string => Boolean(value))))
      .sort((left, right) => left.localeCompare(right, "ko")),
    [organizations],
  );
  const visible = useMemo(
    () => organizations.filter((item) => {
      const nameMatches = !term || item.name.toLocaleLowerCase().includes(term);
      const classMatches = !classification
        || (classification === UNCLASSIFIED ? item.classification === null : item.classification === classification);
      return nameMatches && classMatches;
    }),
    [classification, organizations, term],
  );
  const active = Boolean(term || classification);
  const reset = () => { setQuery(""); setClassification(""); setLimit(DIRECTORY_PAGE_SIZE); };

  return (
    <>
      <div className="roster-toolbar">
        <div>
          <span className="micro-label">Organization directory</span>
          <p className="toolbar-count">
            <strong>{visible.length}곳</strong>
            <span>표시 중 / 전체 {organizations.length}곳</span>
          </p>
        </div>
        <label className="search-field">
          <span className="search-icon" aria-hidden="true">⌕</span>
          <span className="sr-only">기관 이름으로 찾기</span>
          <input
            type="search"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setLimit(DIRECTORY_PAGE_SIZE); }}
            placeholder="기관 이름으로 찾기"
          />
        </label>
      </div>
      {classifications.length > 0 && (
        <div className="directory-filters" aria-label="기관 분류 필터">
          <label className="filter-field">
            <span>ALIO 기관 분류</span>
            <select
              aria-label="ALIO 기관 분류 필터"
              value={classification}
              onChange={(event) => { setClassification(event.target.value); setLimit(DIRECTORY_PAGE_SIZE); }}
            >
              <option value="">전체 분류</option>
              {classifications.map((option) => <option key={option} value={option}>{option}</option>)}
              <option value={UNCLASSIFIED}>분류 공개 정보 없음</option>
            </select>
          </label>
          {active && <button className="clear-filters" type="button" onClick={reset}>필터 초기화</button>}
        </div>
      )}

      {visible.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">∅</span>
          <div>
            <strong>검색 결과가 없습니다.</strong>
            <p>표시된 기관 이름과 공개 분류 값으로만 찾습니다.</p>
            <button className="clear-filters" type="button" onClick={reset}>필터 초기화</button>
          </div>
        </div>
      ) : (
        <div className="organization-list">
          {visible.slice(0, limit).map((organization) => (
            <Link
              className="organization-row"
              href={`/organizations/${organization.id}`}
              key={organization.id}
              aria-label={`${organization.name} · 기관 기록`}
            >
              <span className="organization-avatar" aria-hidden="true">{organization.name.trim().slice(0, 1)}</span>
              <span className="organization-row-main">
                <strong>{organization.name}</strong>
                <span>{organization.classification ?? "분류 공개 정보 없음"}</span>
              </span>
              <span className="organization-row-facts">
                <span><small>현재 임원 공시</small><strong>{organization.executive_count}건</strong></span>
                <span><small>공개 Claim</small><strong>{organization.published_claim_count}건</strong></span>
              </span>
              <span className="row-proof">근거 {organization.evidence_count}개 · 기준일 {organization.as_of ?? "정보 없음"}</span>
              <span className="row-arrow" aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      )}
      {visible.length > limit && (
        <button className="directory-more" type="button" onClick={() => setLimit((current) => current + DIRECTORY_PAGE_SIZE)}>
          {Math.min(DIRECTORY_PAGE_SIZE, visible.length - limit)}곳 더 보기
          <span>{limit} / {visible.length}곳 표시 중</span>
        </button>
      )}
    </>
  );
}
