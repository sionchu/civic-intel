"use client";

import Link from "next/link";
import { useSyncExternalStore, type ReactNode } from "react";

import { formatAuditDate, seoulDate } from "../gukgam/2026/schedule";

// Static home exports pass null; request-time renders pass their KST date. Hydration and a
// minute/focus check keep a tab left open over midnight on the reader's actual KST day.
const subscribe = (onChange: () => void) => {
  const timer = window.setInterval(onChange, 60_000);
  window.addEventListener("focus", onChange);
  return () => {
    window.clearInterval(timer);
    window.removeEventListener("focus", onChange);
  };
};

export function useKstToday(serverToday: string | null): string | null {
  return useSyncExternalStore(subscribe, () => seoulDate(new Date()), () => serverToday);
}

type Relation = "past" | "today" | "upcoming";

function relationOf(date: string, today: string): Relation {
  return date < today ? "past" : date === today ? "today" : "upcoming";
}

function nextDateOf(dates: string[], today: string): string | null {
  return [...dates].sort().find((date) => date >= today) ?? null;
}

export type ScheduleDay = { date: string; count: number; committeeCount: number };
export type ScheduleBriefDay = ScheduleDay & {
  rows: {
    claimId: string;
    organizationId: string;
    organization: string;
    committee: string;
    time: string | null;
    sourcePublishedDate: string;
    pageNumber: number;
  }[];
};

export function KstToday({ serverToday }: { serverToday: string | null }) {
  const today = useKstToday(serverToday);
  return <>{today ? formatAuditDate(today) : "날짜 확인 중"}</>;
}

export function AuditBrief({ serverToday, days }: { serverToday: string | null; days: ScheduleBriefDay[] }) {
  const today = useKstToday(serverToday);
  if (!today) {
    return <p className="coverage-caption">공개된 국감 계획 {days.reduce((sum, day) => sum + day.count, 0).toLocaleString("ko-KR")}건 · <Link href="/gukgam/2026">날짜별 계획 보기</Link></p>;
  }
  const nextDate = nextDateOf(days.map((day) => day.date), today);
  const day = days.find((candidate) => candidate.date === nextDate);
  if (!day) return <p className="coverage-caption">오늘 이후 공개된 감사 계획이 없습니다.</p>;
  return (
    <div className="audit-brief">
      {day.date !== today && <p className="coverage-note">오늘은 공개된 감사 일정이 없습니다.</p>}
      <p className="audit-brief-heading">
        <strong>{day.date === today ? "오늘" : "다음 감사일"} <time dateTime={day.date}>{formatAuditDate(day.date)}</time></strong>
        <span>계획서상 감사 {day.count.toLocaleString("ko-KR")}건 · 위원회 {day.committeeCount.toLocaleString("ko-KR")}곳</span>
      </p>
      <ul className="audit-brief-rows">
        {day.rows.map((row) => (
          <li key={row.claimId}>
            <Link href={`/organizations/${row.organizationId}#claim-${row.claimId}`}>{row.organization}</Link>
            <span>{row.committee} · {row.time || "시간 미기재"}</span>
            <small>계획서 공개 <time dateTime={row.sourcePublishedDate}>{row.sourcePublishedDate}</time> · {row.pageNumber}쪽</small>
          </li>
        ))}
      </ul>
      <p className="audit-brief-more">
        {day.count > day.rows.length && <span>외 {day.count - day.rows.length}건 · </span>}
        <Link href={`/gukgam/2026#audit-${day.date}`}>이날 계획과 근거 보기</Link>
      </p>
    </div>
  );
}

export function NextAuditAction({ serverToday, dates }: { serverToday: string | null; dates: string[] }) {
  const today = useKstToday(serverToday);
  const nextDate = today ? nextDateOf(dates, today) : null;
  return (
    <a className="primary-action" href={nextDate ? `#audit-${nextDate}` : "#gukgam-published-targets-title"}>
      {nextDate && nextDate === today ? "오늘 감사 일정 보기" : "감사 일정 보기"}
    </a>
  );
}

export function AuditDateIndex({ serverToday, days }: { serverToday: string | null; days: ScheduleDay[] }) {
  const today = useKstToday(serverToday);
  const nextDate = today ? nextDateOf(days.map((day) => day.date), today) : null;
  return (
    <nav className="gukgam-date-index" aria-label="감사일별 이동">
      <ol>
        {days.map((day) => {
          const relation = today ? relationOf(day.date, today) : null;
          return (
            <li key={day.date} className={relation ?? undefined}>
              <a href={`#audit-${day.date}`} aria-current={day.date === nextDate ? "date" : undefined}>
                <span>{formatAuditDate(day.date)}</span>
                <small>
                  {relation === "today" ? "오늘 · " : day.date === nextDate ? "다음 · " : ""}
                  {day.count}건
                </small>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function AuditDaySection({
  serverToday,
  date,
  dates,
  count,
  children,
}: {
  serverToday: string | null;
  date: string;
  dates: string[];
  count: number;
  children: ReactNode;
}) {
  const today = useKstToday(serverToday);
  const relation = today ? relationOf(date, today) : null;
  const nextDate = today ? nextDateOf(dates, today) : null;
  return (
    <section id={`audit-${date}`} className={relation ? `gukgam-day ${relation}` : "gukgam-day"} aria-labelledby={`audit-${date}-title`}>
      <header className="gukgam-day-heading">
        <h3 id={`audit-${date}-title`}>{formatAuditDate(date)}</h3>
        <span>
          {relation === null ? "계획 기준" : relation === "today"
            ? "오늘 감사 계획"
            : relation === "past"
              ? "지난 일정 · 계획 기준"
              : date === nextDate ? "다음 감사일" : "예정"}
          {" · "}{count}건
        </span>
      </header>
      {children}
    </section>
  );
}
