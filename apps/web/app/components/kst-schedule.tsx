"use client";

import Link from "next/link";
import { useSyncExternalStore, type ReactNode } from "react";

import { formatAuditDate, seoulDate } from "../gukgam/2026/schedule";

// "Today" is a reader-time fact. A request-time server render passes its KST date; a prebuilt
// snapshot passes null, so nothing reads as 오늘/다음/지난 until the browser's KST date is known.
const subscribe = () => () => {};

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
export type ScheduleBriefRow = { claimId: string; committee: string; organization: string; time: string | null };
export type ScheduleBriefDay = ScheduleDay & { rows: ScheduleBriefRow[] };

const BRIEF_ROWS = 3;

export function KstToday({ serverToday }: { serverToday: string | null }) {
  const today = useKstToday(serverToday);
  return <>{today ? formatAuditDate(today) : "—"}</>;
}

// Home brief: today's audit day, or else the next one, in the canonical schedule order (no ranking).
export function AuditBrief({ serverToday, days }: { serverToday: string | null; days: ScheduleBriefDay[] }) {
  const today = useKstToday(serverToday);
  if (!today) {
    return (
      <p className="coverage-caption">
        공개 감사일 {days.length}일 · 총 {days.reduce((sum, day) => sum + day.count, 0)}건
      </p>
    );
  }
  const nextDate = nextDateOf(days.map((day) => day.date), today);
  const day = days.find((candidate) => candidate.date === nextDate);
  if (!day) return <p className="coverage-caption">남은 공개 감사 일정이 없습니다.</p>;
  const isToday = day.date === today;
  return (
    <div className="audit-brief">
      {!isToday && <p className="coverage-caption">오늘은 공개된 감사 일정이 없습니다.</p>}
      <p className="audit-brief-heading">
        <strong>{isToday ? "오늘" : "다음 감사일"} {formatAuditDate(day.date)}</strong>
        <span>감사 {day.count}건 · 위원회 {day.committeeCount}곳</span>
      </p>
      <ul className="audit-brief-rows">
        {day.rows.slice(0, BRIEF_ROWS).map((row) => (
          <li key={row.claimId}>
            <strong>{row.organization}</strong>
            <span>{[row.committee, row.time].filter(Boolean).join(" · ")}</span>
          </li>
        ))}
      </ul>
      <p className="audit-brief-more">
        {day.count > BRIEF_ROWS && <span>외 {day.count - BRIEF_ROWS}건 · </span>}
        <Link href={`/gukgam/2026#audit-${day.date}`}>이날 일정 전체 보기</Link>
      </p>
    </div>
  );
}

export function NextAuditAction({ serverToday, dates }: { serverToday: string | null; dates: string[] }) {
  const today = useKstToday(serverToday);
  const nextDate = today ? nextDateOf(dates, today) : null;
  return (
    <a className="primary-action" href={nextDate ? `#audit-${nextDate}` : "#gukgam-published-targets-title"}>
      {nextDate !== null && nextDate === today ? "오늘 감사 일정 보기" : "감사 일정 보기"}
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
          const relation = today ? relationOf(day.date, today) : undefined;
          return (
            <li key={day.date} className={relation}>
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
    <section
      id={`audit-${date}`}
      className={relation ? `gukgam-day ${relation}` : "gukgam-day"}
      aria-labelledby={`audit-${date}-title`}
    >
      <header className="gukgam-day-heading">
        <h3 id={`audit-${date}-title`}>{formatAuditDate(date)}</h3>
        <span>
          {relation === null
            ? "계획 기준"
            : relation === "today"
              ? "오늘 열리는 감사 일정"
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
