import Link from "next/link";

import { getGukgamWitnesses } from "../data";
import type { GukgamWitnessProjectionItem } from "../types";
import ReadState from "./read-state";
import "./gukgam-witnesses.css";

const CATEGORIES: GukgamWitnessProjectionItem["category"][] = ["증인", "참고인"];

function groupByCommittee(
  items: GukgamWitnessProjectionItem[],
): [string, GukgamWitnessProjectionItem[]][] {
  const groups = new Map<string, GukgamWitnessProjectionItem[]>();
  for (const item of items) {
    const group = groups.get(item.committee_name) ?? [];
    group.push(item);
    groups.set(item.committee_name, group);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, "ko-KR"));
}

function locatorLabel(item: GukgamWitnessProjectionItem): string {
  const place =
    item.page_number === null
      ? `표 ${item.table_index} ${item.table_row}행`
      : `p.${item.page_number}`;
  return `${place}, ${item.row_number}번`;
}

// Server component. Names are source-listed text. A Person link appears only when a reviewed,
// separately published Person Claim restates this exact row.
export default async function GukgamWitnesses() {
  const result = await getGukgamWitnesses();
  if (result.state === "error") return <ReadState error={result.error} />;
  const projection = result.data;

  return (
    <section className="gukgam-witnesses" aria-labelledby="gukgam-witnesses-title">
      <h2 id="gukgam-witnesses-title">위원회 공식 증인·참고인 명단</h2>
      <p className="gukgam-witnesses-note">
        위원회가 의결한 출석요구 명단입니다. 출석 요구일 뿐 위법 판단이 아닙니다.
      </p>
      {projection.items.length === 0 ? (
        <p className="gukgam-witnesses-empty">
          아직 공개된 명단이 없습니다.
        </p>
      ) : (
        groupByCommittee(projection.items).map(([committee, committeeItems]) => (
          <div className="gukgam-witnesses-committee" key={committee}>
            <h3>{committee}</h3>
            {CATEGORIES.map((category) => {
              const rows = committeeItems.filter((item) => item.category === category);
              if (rows.length === 0) return null;
              return (
                <div className="gukgam-witnesses-category" key={category}>
                  <h4>
                    {category} <span>{rows.length}명</span>
                  </h4>
                  <ul>
                    {rows.map((item) => (
                      <li key={item.claim_id} id={`witness-${item.claim_id}`}>
                        <strong>
                          {item.linked_person ? (
                            <Link href={`/people/${item.linked_person.id}`}>{item.name}</Link>
                          ) : item.name}
                        </strong>
                        <span className="gukgam-witnesses-tag">
                          {item.source_tag}
                          {item.acquisition_channel === "OWNER_SUPPLIED_COPY" ? " · 아직 공식 발표 아님" : ""}
                        </span>
                        <span>{item.affiliation_title ?? "소속·직위 미기재"}</span>
                        {item.attendance_date_text ? (
                          <span className="gukgam-witnesses-date">
                            출석 {item.attendance_date_text}
                          </span>
                        ) : null}
                        <small>
                          {item.list_version}
                          {item.adoption_date ? ` · ${item.adoption_date} 의결` : ""} ·{" "}
                          {item.source_url ? (
                            <a href={item.source_url} rel="noreferrer noopener">
                              공식 출처 ({locatorLabel(item)})
                            </a>
                          ) : (
                            <span className="gukgam-witnesses-provenance">
                              {item.provenance_label} ({locatorLabel(item)})
                            </span>
                          )}
                        </small>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        ))
      )}
      <p className="gukgam-witnesses-limitations">전체 명단이 아니며, 의결에 따라 바뀔 수 있습니다. 사람이 검토해 공개한 행만 인물 기록과 연결합니다.</p>
    </section>
  );
}
