"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { adminRequest } from "./admin-types";
import type {
  GukgamClaimReviewItem,
  GukgamReviewDecision,
  GukgamReviewEvidenceOpens,
  GukgamReviewHoldReason,
  GukgamReviewThroughput,
} from "./operator-types";

const IDLE_THRESHOLD_MS = 300_000;

const HOLD_REASONS: Record<GukgamReviewHoldReason, string> = {
  INSTITUTION_IDENTITY_UNCLEAR: "기관 동일성 불명확",
  LIFECYCLE_OR_SUCCESSOR_UNCLEAR: "개편·승계 관계 불명확",
  SOURCE_CONTEXT_INSUFFICIENT: "현재 근거 문맥 부족",
  OTHER_EVIDENCE_REQUIRED: "추가 근거 필요",
};

type Session = {
  reviewKey: string;
  openedAt: number;
  lastActivityAt: number;
  activeMs: number;
  evidenceOpens: GukgamReviewEvidenceOpens;
};

type ReceiptResponse = {
  review_key: string;
  receipt_sha256: string;
  replayed: boolean;
  canonical_write_performed: false;
  claim_commit_authorized: false;
};

function recordLink(kind: string, id: string): string {
  const query = new URLSearchParams({
    tab: "records",
    kind,
    focus_kind: kind,
    focus_id: id,
  });
  return "/admin/review?" + query.toString();
}

function duration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 60_000) return String(Math.round(ms / 1000)) + "초";
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return String(minutes) + "분 " + String(seconds) + "초";
}

function decisionLabel(decision: GukgamReviewDecision): string {
  return {
    APPROVE: "APPROVE",
    REJECT: "REJECT",
    HOLD: "HOLD",
  }[decision];
}

export default function GukgamReviewThroughputPanel({
  items,
  manifestSha256,
  throughput,
}: {
  items: GukgamClaimReviewItem[];
  manifestSha256: string;
  throughput: GukgamReviewThroughput | null;
}) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [holdReason, setHoldReason] = useState<GukgamReviewHoldReason | "">("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const latestByKey = useMemo(
    () => new Map((throughput?.items ?? []).map((item) => [item.review_key, item])),
    [throughput],
  );
  const positions = useMemo(() => {
    const groups = new Map<string, GukgamClaimReviewItem[]>();
    for (const item of items) {
      const group = groups.get(item.organization_id) ?? [];
      group.push(item);
      groups.set(item.organization_id, group);
    }
    const result = new Map<string, { index: number; count: number }>();
    for (const group of groups.values()) {
      group.sort((a, b) =>
        a.audit_date.localeCompare(b.audit_date) || a.review_key.localeCompare(b.review_key));
      group.forEach((item, index) =>
        result.set(item.review_key, { index: index + 1, count: group.length }));
    }
    return result;
  }, [items]);

  function start(item: GukgamClaimReviewItem) {
    const now = Date.now();
    setSession({
      reviewKey: item.review_key,
      openedAt: now,
      lastActivityAt: now,
      activeMs: 0,
      evidenceOpens: { organization: 0, gukgam_observation: 0 },
    });
    setHoldReason("");
    setMessage("");
    setError("");
  }

  function touch() {
    const now = Date.now();
    setSession((current) => current ? {
      ...current,
      activeMs: current.activeMs + Math.min(now - current.lastActivityAt, IDLE_THRESHOLD_MS),
      lastActivityAt: now,
    } : current);
  }

  function evidenceOpen(
    reviewKey: string,
    kind: keyof GukgamReviewEvidenceOpens,
    now: number,
  ) {
    setSession((current) => {
      if (!current || current.reviewKey !== reviewKey) return current;
      return {
        ...current,
        activeMs: current.activeMs + Math.min(now - current.lastActivityAt, IDLE_THRESHOLD_MS),
        lastActivityAt: now,
        evidenceOpens: {
          ...current.evidenceOpens,
          [kind]: current.evidenceOpens[kind] + 1,
        },
      };
    });
  }

  async function decide(decision: GukgamReviewDecision) {
    if (!session || busy) return;
    if (decision === "HOLD" && !holdReason) {
      setError("HOLD 사유를 먼저 선택하세요.");
      return;
    }
    const now = Date.now();
    const activeMs = session.activeMs
      + Math.min(now - session.lastActivityAt, IDLE_THRESHOLD_MS);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const receipt = await adminRequest<ReceiptResponse>("gukgam_review_metric", {
        request_id: crypto.randomUUID(),
        manifest_sha256: manifestSha256,
        review_key: session.reviewKey,
        opened_at: new Date(session.openedAt).toISOString(),
        decided_at: new Date(now).toISOString(),
        active_ms: activeMs,
        decision,
        hold_reason: decision === "HOLD" ? holdReason : null,
        evidence_opens: session.evidenceOpens,
        batch_decided: false,
      });
      setMessage(
        "리뷰 receipt 저장됨 · " + receipt.review_key + " · "
        + decisionLabel(decision) + " · canonical commit 없음",
      );
      setSession(null);
      setHoldReason("");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "리뷰 receipt 저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  const overall = throughput?.overall;
  const decidedCount = throughput?.decided_count ?? 0;
  const holdCount = overall?.decision_counts.HOLD ?? 0;
  const evidenceCount = overall?.with_evidence_opens ?? 0;
  const holdRate = decidedCount ? Math.round((holdCount / decidedCount) * 100) : 0;
  const evidenceRate = overall?.evidence_open_rate === null || overall?.evidence_open_rate === undefined
    ? 0
    : Math.round(overall.evidence_open_rate * 100);

  return <div className="review-throughput">
    <div className="review-throughput-summary" aria-label="국감 검토 처리량">
      <div><small>결정 처리 기록</small><strong>{throughput?.decided_count ?? 0} / {items.length}</strong></div>
      <div><small>활동 시간 중앙값</small><strong>{duration(overall?.median_active_ms ?? null)}</strong></div>
      <div><small>활동 시간 90백분위</small><strong>{duration(overall?.p90_active_ms ?? null)}</strong></div>
      <div><small>첫 기재 건 중앙값</small><strong>{duration(throughput?.first_occurrence.median_active_ms ?? null)}</strong></div>
      <div><small>반복 기재 건 중앙값</small><strong>{duration(throughput?.repeat_occurrence.median_active_ms ?? null)}</strong></div>
      <div><small>보류 / 근거 열람</small><strong>{holdCount} ({holdRate}%) / {evidenceCount} ({evidenceRate}%)</strong></div>
    </div>
    <p className="operator-note">
      시간은 5분 유휴 시간 상한을 적용한 상호작용 기반 활동 시간 추정치입니다. 이 처리 기록의
      승인·제외·보류는 항목별 사람 검토 기록이며, 검토된 목록 생성이나 공개 기록의 확정 반영을 자동 승인하지 않습니다. 행정안전부 기관 70개 검토와도 별도 지표입니다.
    </p>
    {!throughput && <p className="admin-error" role="alert">
      현재 검토 목록과 연결된 처리량 처리 기록을 읽을 수 없어 결정 기록을 비활성화했습니다.
    </p>}
    {message && <p className="admin-receipt" role="status">{message}</p>}
    {error && <p className="admin-error" role="alert">{error}</p>}

    <div className="operator-table-scroll">
      <table className="operator-table">
        <thead><tr>
          <th>기관</th><th>위원회 / 감사 예정일</th><th>근거·현재 상태</th><th>사람 리뷰 처리 기록</th>
        </tr></thead>
        <tbody>{items.map((item) => {
          const latest = latestByKey.get(item.review_key);
          const position = positions.get(item.review_key);
          const active = session?.reviewKey === item.review_key;
          const anotherActive = Boolean(session && !active);
          return <tr key={item.review_key} data-review-active={active}>
            <td>
              <strong>{item.organization_name}</strong>
              <small>{item.review_key}</small>
              <small>기관 기재 건 {position?.index ?? "—"} / {position?.count ?? "—"}</small>
            </td>
            <td>{item.committee_name}<small>{item.audit_date}</small></td>
            <td>
              <span className="operator-tag">{item.match_class}</span>
              <small>기록 존재 {item.current_claim_present ? "예" : "아니요"} · 저장 반영 승인되지 않음</small>
              <div className="review-evidence-links">
                <Link
                  href={recordLink("organizations", item.organization_id)}
                  target="_blank"
                  prefetch={false}
                  onClick={() => evidenceOpen(item.review_key, "organization", Date.now())}
                >기관 ↗</Link>
                <Link
                  href={recordLink("observations", item.observation_id)}
                  target="_blank"
                  prefetch={false}
                  onClick={() => evidenceOpen(item.review_key, "gukgam_observation", Date.now())}
                >일정 수집 기록 ↗</Link>
              </div>
            </td>
            <td>
              {latest && <div className="review-latest">
                <strong>{decisionLabel(latest.decision)}</strong>
                <small>활동 시간 {duration(latest.active_ms)} · 근거 열람 {
                  Object.values(latest.evidence_opens).reduce((sum, value) => sum + value, 0)
                }회</small>
                {latest.hold_reason && <small>{HOLD_REASONS[latest.hold_reason]}</small>}
              </div>}
              {!active && <button
                type="button"
                className="review-start"
                disabled={!throughput || anotherActive || busy}
                onClick={() => start(item)}
              >{latest ? "재검토 시작" : "검토 시작"}</button>}
              {active && <div className="review-decision">
                <small>타이머 시작됨 · 근거 링크는 새 탭으로 열립니다.</small>
                <label>
                  보류 사유
                  <select
                    value={holdReason}
                    onChange={(event) => {
                      touch();
                      setHoldReason(event.target.value as GukgamReviewHoldReason | "");
                    }}
                  >
                    <option value="">보류일 때만 선택</option>
                    {Object.entries(HOLD_REASONS).map(([value, label]) =>
                      <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                <div className="admin-button-row">
                  <button disabled={busy} type="button" onClick={() => decide("APPROVE")}>승인</button>
                  <button disabled={busy} type="button" onClick={() => decide("REJECT")}>제외</button>
                  <button disabled={busy || !holdReason} type="button" onClick={() => decide("HOLD")}>보류</button>
                  <button disabled={busy} type="button" onClick={() => {
                    setSession(null);
                    setHoldReason("");
                    setMessage("");
                    setError("");
                  }}>취소 · 처리 기록 없음</button>
                </div>
              </div>}
            </td>
          </tr>;
        })}</tbody>
      </table>
    </div>
  </div>;
}
