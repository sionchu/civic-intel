import type { ReactNode } from "react";

import { formatDay } from "./evidence-panel";

// Shared Person/Organization reading header: what the record is, its identity status and the
// coverage counts a reader needs before trusting it. Counts describe what is published here; they
// are not a measure of the subject.
export default function RecordHeader({
  kind,
  name,
  status,
  lede,
  claimCount,
  sourceCount,
  recordedAt,
  aside,
}: {
  kind: string;
  name: string;
  status: ReactNode;
  lede: string;
  claimCount: number;
  sourceCount: number;
  recordedAt: string | null;
  aside?: ReactNode;
}) {
  return (
    <header className="profile-header record-header">
      <div>
        <p className="eyebrow">{kind}</p>
        <div className="profile-title-row">
          <h1>{name}</h1>
          {status}
        </div>
        <p className="profile-lede">{lede}</p>
        <dl className="record-meta" aria-label="이 기록의 공개 범위">
          <div><dt>공개 Claim</dt><dd>{claimCount}건</dd></div>
          <div><dt>출처</dt><dd><a href="#sources">{sourceCount}개</a></dd></div>
          <div>
            <dt>최근 기록 반영</dt>
            <dd>
              {formatDay(recordedAt) ?? "미기재"}
              <small>Civic Intel 기록 시각 · 실제 사건일이 아님</small>
            </dd>
          </div>
        </dl>
      </div>
      {aside}
    </header>
  );
}
