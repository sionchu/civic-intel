import { statusLabel } from "../display-labels";
import Link from "next/link";

import type { GukgamCommittee } from "../types";

// Read-only member disclosure for one Gukgam committee. Every row is a published
// ASSEMBLY_COMMITTEES Claim of a public Person; "근거" opens that Claim's evidence on the profile.
export default function CommitteeMembers({
  committee,
  label = "감사 위원",
  open = false,
}: {
  committee: GukgamCommittee;
  label?: string;
  open?: boolean;
}) {
  return (
    <details className="committee-members" open={open}>
      <summary>
        {label} {committee.member_count}명
      </summary>
      {committee.members.length === 0 ? (
        <p className="committee-members-empty" role="status">
          <span className="status UNKNOWN">{statusLabel("UNKNOWN")}</span> 아직 공개된 위원 기록이 없습니다.
        </p>
      ) : (
        <ul className="committee-member-list">
          {committee.members.map((member) => (
            <li key={member.person.id}>
              <Link className="committee-member-name" href={`/people/${member.person.id}`}>
                {member.person.name}
              </Link>
              <span className="committee-member-party">{member.party ?? "정당 정보 없음"}</span>
              <span className={`status ${member.epistemic_status}`}>{statusLabel(member.epistemic_status)}</span>
              <Link
                className="committee-member-evidence"
                href={`/people/${member.person.id}#claim-${member.claim_id}`}
              >
                근거
              </Link>
            </li>
          ))}
        </ul>
      )}
      <small className="committee-members-note">
        국회 명부 기준 위원입니다. 감사 당일 출석이나 피감기관 질의를 뜻하지 않습니다.
      </small>
    </details>
  );
}
