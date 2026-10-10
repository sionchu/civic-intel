/** Display source date units without presenting a normalized month/year anchor as an exact day. */
export function statedDate(value: unknown, precision: unknown): string | null {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  if (precision === "YEAR") return `${value.slice(0, 4)}년`;
  if (precision === "MONTH") return `${value.slice(0, 4)}년 ${Number(value.slice(5, 7))}월`;
  if (precision === "DAY") return `${value.slice(0, 4)}.${value.slice(5, 7)}.${value.slice(8, 10)}`;
  return null;
}

export function careerPeriodText(value: unknown): string {
  if (!value || typeof value !== "object") return "기간 미기재";
  const period = value as Record<string, unknown>;
  const start = statedDate(period.start, period.start_precision);
  const end = statedDate(period.end, period.end_precision);
  const point = statedDate(period.point, period.point_precision);
  if (point && !start && !end) return point;
  if (start || end) return `${start ?? "시작 미기재"} – ${end ?? (period.ongoing === true ? "출처에 계속 재직으로 기재" : "종료 미기재")}`;
  return "기간 미기재";
}

export function careerAttribution(semantics: unknown): string | null {
  if (semantics === "SOURCE_ATTRIBUTED_BIOGRAPHY") return "국회 약력 기재";
  if (semantics === "CANDIDATE_SUBMITTED_CAREER") return "후보자 제출 경력";
  if (semantics === "HISTORICAL_ASSEMBLY_TERM") return "역대 국회의원 임기";
  return null;
}
