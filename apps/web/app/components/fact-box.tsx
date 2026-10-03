import type { ReactNode } from "react";

import type { Claim } from "../types";
import { formatDay } from "./evidence-panel";

export type FactRow = {
  key: string;
  label: string;
  value: ReactNode;
  claim?: Claim;
  derived?: { href: string };
};

// "핵심 기록": one row per real published Claim (or one labelled derived count). The 근거 link jumps
// to the Claim's evidence panel on the same page.
export default function FactBox({ rows }: { rows: FactRow[] }) {
  if (rows.length === 0) return null;
  return (
    <table className="fact-table">
      <thead>
        <tr><th scope="col">항목</th><th scope="col">내용</th><th scope="col">상태</th><th scope="col">기준일</th><th scope="col">근거</th></tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.key}>
            <th scope="row">{row.label}</th>
            <td>{row.value}</td>
            <td>
              {row.claim ? (
                <span className={`status ${row.claim.epistemic_status}`}>{row.claim.epistemic_status}</span>
              ) : (
                <span className="status DERIVED">집계</span>
              )}
              {row.claim?.source_conflict && <span className="status CONFLICT">SOURCE CONFLICT</span>}
            </td>
            <td>{row.claim ? formatDay(row.claim.valid_from) ?? "미기재" : "—"}</td>
            <td>
              {row.claim ? <a href={`#claim-${row.claim.id}`}>근거</a> : row.derived ? <a href={row.derived.href}>목록</a> : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
