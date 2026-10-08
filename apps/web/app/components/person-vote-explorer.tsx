"use client";

import { statusLabel } from "../display-labels";

import { useEffect, useState } from "react";
import { selectVoteRecords, type OfficialVoteRecord } from "../person-activity";
import { usePersonEvidence } from "./person-evidence-context";
import EvidencePanel from "./evidence-panel";
import type { Claim, Source } from "../types";

const EMPTY_CLAIMS: Claim[] = [];
const EMPTY_SOURCES: Source[] = [];

export default function PersonVoteExplorer({ records, claims: providedClaims, sources: providedSources, existingClaimIds = [], eligibleCount, inputScope }: { records: OfficialVoteRecord[]; claims?: Claim[]; sources?: Source[]; existingClaimIds?: string[]; eligibleCount?: number; inputScope?: string }) {
  const shared = usePersonEvidence();
  const claims = providedClaims ?? shared?.claims ?? EMPTY_CLAIMS;
  const sources = providedSources ?? shared?.sources ?? EMPTY_SOURCES;
  const [query, setQuery] = useState("");
  const [committee, setCommittee] = useState("ALL");
  const [limit, setLimit] = useState(20);
  const [activeId, setActiveId] = useState<string | null>(null);
  const countKnown = Number.isSafeInteger(eligibleCount) && (eligibleCount ?? -1) >= 0;
  const complete = countKnown && inputScope === "PUBLISHED_SOURCE_VALIDATED_SUBJECT_VOTES" && eligibleCount === records.length;
  const activeClaim = claims.find((claim) => claim.id === activeId);
  useEffect(() => {
    const reveal = (hash: string) => {
      let id: string;
      try { id = decodeURIComponent(hash.replace(/^#claim-/, "")); } catch { return; }
      if (!hash.startsWith("#claim-") || existingClaimIds.includes(id)) return;
      if (records.some((record) => record.claimId === id) && claims.some((claim) => claim.id === id)) setActiveId(id);
    };
    const fromHash = () => reveal(window.location.hash);
    const onClick = (event: MouseEvent) => {
      const href = (event.target as Element | null)?.closest('a[href^="#claim-"]')?.getAttribute("href");
      if (href) reveal(href);
    };
    fromHash(); window.addEventListener("hashchange", fromHash); document.addEventListener("click", onClick);
    return () => { window.removeEventListener("hashchange", fromHash); document.removeEventListener("click", onClick); };
  }, [records, claims, existingClaimIds]);
  useEffect(() => {
    if (!activeClaim) return;
    const target = document.getElementById(`claim-${activeClaim.id}`);
    const disclosure = target?.querySelector<HTMLDetailsElement>(":scope > details.evidence-disclosure");
    if (disclosure) disclosure.open = true;
    target?.scrollIntoView({ block: "start" });
  }, [activeClaim]);
  const committees = [...new Set(records.flatMap((record) => record.committee ? [record.committee] : []))].sort();
  const unknown = records.filter((record) => record.committee === null).length;
  const selected = selectVoteRecords(records, query, committee);
  return (
    <section className="person-section" id="vote-records" aria-labelledby="vote-records-title">
      <div className="section-intro"><h2 id="vote-records-title">법안별 표결 기록</h2></div>
      <p className="section-note">이 화면에 연결된 법안 표결을 제목과 원자료의 소관위원회로 찾습니다. 위원회 분류는 정책성향을 뜻하지 않습니다. 불참은 반대가 아니며 사유는 이 기록으로 알 수 없습니다.</p>
      <div className="vote-filters">
        <label htmlFor="vote-title-query">법안 제목<input id="vote-title-query" type="search" value={query} placeholder="제목에 포함된 단어" onChange={(event) => { setQuery(event.target.value); setLimit(20); }} /></label>
        <label htmlFor="vote-committee">소관위원회<select id="vote-committee" value={committee} onChange={(event) => { setCommittee(event.target.value); setLimit(20); }}>
          <option value="ALL">전체 ({records.length}건)</option>
          {committees.map((name) => <option key={name} value={name}>{name} ({records.filter((record) => record.committee === name).length}건)</option>)}
          <option value="UNKNOWN">소관위원회 미기재 ({unknown}건)</option>
        </select></label>
      </div>
      <p className="section-note" role="status" aria-live="polite">{selected.length}건 / 연결된 공개 표결 {records.length}건 · 현재 {Math.min(limit, selected.length)}건 표시 · <span className="status DERIVED">{statusLabel("DERIVED")}</span> 원자료 분류·제목 검색 결과</p>
      <p className="section-note">{complete ? `공개 기준을 통과한 표결 ${records.length.toLocaleString("ko-KR")}건이 모두 연결되었습니다.` : countKnown && eligibleCount !== records.length ? `공개 대상 ${eligibleCount!.toLocaleString("ko-KR")}건과 이 화면의 연결 기록 ${records.length.toLocaleString("ko-KR")}건이 일치하지 않습니다. 일부 기록만 확인할 수 있습니다.` : "이 화면에 연결된 기록을 표시합니다. 공개 표결 전체가 포함되었는지는 확인되지 않았습니다."}</p>
      {records.length === 0 ? <p className="empty-note">이 화면에서 확인할 수 있는 근거 연결된 공개 표결 기록이 없습니다. 미수집·미공개 기록의 수는 알 수 없습니다.</p> : selected.length === 0 ? <p className="empty-note">선택한 위원회와 제목에 맞는 공개 기록이 없습니다.</p> : (
        <ol className="vote-rows">
          {selected.slice(0, limit).map((record) => <li className="vote-row" key={record.claimId}>
            {record.date ? <time className="vote-date" dateTime={record.date}>{record.date}</time> : <span className="vote-date">날짜 미기재·형식 미확인</span>}
            <span className="vote-bill"><a href={`#claim-${record.claimId}`} onClick={() => { if (!existingClaimIds.includes(record.claimId)) setActiveId(record.claimId); }}>{record.title}</a><small className="claim-date">{record.committee ?? "소관위원회 미기재"} · 의안 {record.billId}</small></span>
            <span className="status AVAILABLE vote-value">{record.choice}</span>
            <div className="vote-trace source-links"><span className={`status ${record.status}`}>{statusLabel(record.status)}</span><a href={`#claim-${record.claimId}`} onClick={() => { if (!existingClaimIds.includes(record.claimId)) setActiveId(record.claimId); }}>근거 기록 열기</a>{record.sourceConflict && <span className="status conflict">{statusLabel("CONFLICT")}</span>}{record.sourceIds.map((id, index) => <a key={id} href={`#source-${id}`}>출처 {index + 1}</a>)}</div>
          </li>)}
        </ol>
      )}
      {selected.length > limit && <button className="load-more" type="button" onClick={() => setLimit(limit + 20)}>표결 기록 더 보기</button>}
      {activeClaim && !existingClaimIds.includes(activeClaim.id) && <EvidencePanel claim={activeClaim} sourceById={new Map(sources.map((source) => [source.id, source]))} kind="선택한 표결 기록" />}
      <p className="section-note"><a href="#records">전체 기록과 근거 보기</a> · 각 찬반은 표시된 법안에 대한 표결이며 다른 정책 입장이나 개인의 신념을 단정하지 않습니다.</p>
    </section>
  );
}
