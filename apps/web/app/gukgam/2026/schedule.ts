// Pure presentation grouping over the public Claim-backed Gukgam target projection.
// It only reorders already-published items by plan date and committee; it never adds,
// infers or removes targets; ordering is calendar/alphabetical only and carries no judgment.

export type ScheduleItem = {
  organization: { id: string; name: string };
  committee_name: string;
  audit_date: string;
  time_text: string | null;
  claim_id: string;
};

export type CommitteeGroup<T extends ScheduleItem> = { committee: string; items: T[] };
export type DateGroup<T extends ScheduleItem> = {
  date: string;
  relation: "past" | "today" | "upcoming";
  committees: CommitteeGroup<T>[];
  count: number;
};

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

export function seoulDate(now: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

// The KST date a server render may present as 오늘. A Sites snapshot is rendered at build time,
// so its build date is not the reader's date: it renders no relative day until hydration.
export function renderedKstToday(now: Date): string | null {
  return process.env.CIVIC_SITES_EXPORT === "1" ? null : seoulDate(now);
}

export function formatAuditDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  const weekday = WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()];
  return `${month}월 ${day}일 (${weekday})`;
}

function compareText(left: string, right: string): number {
  return left.localeCompare(right, "ko");
}

export function groupByDateAndCommittee<T extends ScheduleItem>(items: T[], today: string): DateGroup<T>[] {
  const byDate = new Map<string, Map<string, T[]>>();
  for (const item of items) {
    const committees = byDate.get(item.audit_date) ?? new Map<string, T[]>();
    const rows = committees.get(item.committee_name) ?? [];
    rows.push(item);
    committees.set(item.committee_name, rows);
    byDate.set(item.audit_date, committees);
  }
  return [...byDate.keys()].sort().map((date) => {
    const committees = [...byDate.get(date)!.entries()]
      .sort(([left], [right]) => compareText(left, right))
      .map(([committee, rows]) => ({
        committee,
        items: [...rows].sort(
          (left, right) =>
            compareText(left.time_text ?? "", right.time_text ?? "")
            || compareText(left.organization.name, right.organization.name)
            || compareText(left.claim_id, right.claim_id),
        ),
      }));
    return {
      date,
      relation: date < today ? "past" : date === today ? "today" : "upcoming",
      committees,
      count: committees.reduce((total, group) => total + group.items.length, 0),
    };
  });
}

export function focusDate<T extends ScheduleItem>(groups: DateGroup<T>[]): string | null {
  return groups.find((group) => group.relation !== "past")?.date ?? null;
}
