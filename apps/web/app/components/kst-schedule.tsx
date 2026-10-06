"use client";

import Link from "next/link";
import { useSyncExternalStore, type ReactNode } from "react";

import { formatAuditDate, seoulDate } from "../gukgam/2026/schedule";

// "Today" is a reader-time fact. The server passes the date it rendered with; after hydration the
// browser's KST date wins, so a prebuilt snapshot never shows a stale 오늘/다음/지난 label.
const subscribe = () => () => {};

export function useKstToday(serverToday: string): string {
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

export function KstToday({ serverToday }: { serverToday: string }) {
  return <>{formatAuditDate(useKstToday(serverToday))}</>;
}

export function TodayAuditLine({ serverToday, days }: { serverToday: string; days: ScheduleDay[] }) {
  const today = useKstToday(serverToday);
  const todayDay = days.find((day) => day.date === today);
  const nextDate = nextDateOf(days.map((day) => day.date), today);
  if (todayDay) {
    return (
      <>
        <p className="coverage-value"><strong>{todayDay.count}</strong><span>건</span></p>
        <p className="coverage-caption">
          오늘 공개 기준을 통과한 감사 일정 · {todayDay.committeeCount}개 위원회
        </p>
        <Link className="inline-action" href={`/gukgam/2026#audit-${today}`}>오늘 일정 보기 <span aria-hidden="true">↗</span></Link>
      </>
    );
  }
  return (
    <>
      <p className="coverage-caption">현재 공개 기준에서 오늘 표시할 일정이 없습니다.</p>
      {nextDate && (
        <Link className="inline-action" href={`/gukgam/2026#audit-${nextDate}`}>
          다음 공개 일정 {formatAuditDate(nextDate)} <span aria-hidden="true">↗</span>
        </Link>
      )}
    </>
  );
}

export function NextAuditAction({ serverToday, dates }: { serverToday: string; dates: string[] }) {
  const today = useKstToday(serverToday);
  const nextDate = nextDateOf(dates, today);
  return (
    <a className="primary-action" href={nextDate ? `#audit-${nextDate}` : "#gukgam-published-targets-title"}>
      {nextDate === today ? "오늘 감사 일정 보기" : "감사 일정 보기"} <span aria-hidden="true">↓</span>
    </a>
  );
}

export function AuditDateIndex({ serverToday, days }: { serverToday: string; days: ScheduleDay[] }) {
  const today = useKstToday(serverToday);
  const nextDate = nextDateOf(days.map((day) => day.date), today);
  return (
    <nav className="gukgam-date-index" aria-label="감사일별 이동">
      <ol>
        {days.map((day) => {
          const relation = relationOf(day.date, today);
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
  serverToday: string;
  date: string;
  dates: string[];
  count: number;
  children: ReactNode;
}) {
  const today = useKstToday(serverToday);
  const relation = relationOf(date, today);
  const nextDate = nextDateOf(dates, today);
  return (
    <section id={`audit-${date}`} className={`gukgam-day ${relation}`} aria-labelledby={`audit-${date}-title`}>
      <header className="gukgam-day-heading">
        <h3 id={`audit-${date}-title`}>{formatAuditDate(date)}</h3>
        <span>
          {relation === "today"
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
