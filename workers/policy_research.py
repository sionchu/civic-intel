from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass

from packages.connectors.nkis_research import (
    MissingNkisApiKey,
    NkisApiError,
    NkisResearchOutput,
    NkisResearchReportConnector,
    nkis_research_policy,
    responsible_researcher_candidate_name,
)
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class StagedResearchOutput:
    output: NkisResearchOutput
    candidate: IdentityCandidate | None

    def to_dict(self) -> dict[str, object]:
        return {
            "output_id": self.output.output_id,
            "sequence": self.output.sequence,
            "title": self.output.title,
            "publisher": self.output.publisher,
            "publication_year": self.output.publication_year,
            "responsible_researcher_text": self.output.responsible_researcher_text,
            "large_category": {
                "code": self.output.large_category_code,
                "name": self.output.large_category_name,
            },
            "middle_category": {
                "code": self.output.middle_category_code,
                "name": self.output.middle_category_name,
            },
            "original_url": self.output.original_url,
            "researcher_candidate": (
                {
                    "canonical_name": self.candidate.canonical_name,
                    "organization": self.candidate.organization,
                    "office": self.candidate.office,
                    "identity_anchors": list(self.candidate.career_anchors),
                    "semantics": (
                        "NKIS가 이 연구성과의 단일 연구책임자로 표시한 사람 후보이다. "
                        "발행기관 재직 사실은 별도 공식 프로필로 검증해야 한다."
                    ),
                }
                if self.candidate
                else None
            ),
            "provenance_semantics": (
                "NKIS 연구성과 메타데이터는 연구성과·책임자 표기를 증명하지만, "
                "발행기관의 고용관계나 현재 재직을 자동 증명하지 않는다."
            ),
        }


def output_to_identity(output: NkisResearchOutput) -> IdentityCandidate | None:
    name = responsible_researcher_candidate_name(output.responsible_researcher_text)
    if name is None:
        return None
    return IdentityCandidate(
        canonical_name=name,
        office="연구책임자(해당 연구성과)",
        organization=None,
        career_anchors=(
            f"nkis_output_id:{output.output_id}",
            f"nkis_output_sequence:{output.sequence}",
            f"nkis_publication_year:{output.publication_year}",
            f"nkis_publisher:{output.publisher}",
        ),
    )


def stage_outputs(outputs: list[NkisResearchOutput]) -> list[StagedResearchOutput]:
    return [StagedResearchOutput(output, output_to_identity(output)) for output in outputs]


def repeated_research_topics(
    outputs: list[NkisResearchOutput], *, minimum_outputs: int = 2
) -> list[dict[str, object]]:
    """Derive review candidates without pretending name-text grouping resolves identity."""

    if minimum_outputs < 2:
        raise ValueError("research topic inference requires at least two outputs")

    unique_outputs: dict[tuple[str, str], NkisResearchOutput] = {}
    for output in outputs:
        unique_outputs[(output.output_id, output.sequence)] = output

    grouped_topics: dict[tuple[str, str], list[str]] = defaultdict(list)
    for output in unique_outputs.values():
        researcher = responsible_researcher_candidate_name(output.responsible_researcher_text)
        topic = output.middle_category_name or output.large_category_name
        if researcher and topic:
            grouped_topics[(researcher, output.publisher)].append(topic)

    derived: list[dict[str, object]] = []
    for (researcher, publisher), topics in sorted(grouped_topics.items()):
        for topic, count in sorted(Counter(topics).items()):
            if count >= minimum_outputs:
                derived.append(
                    {
                        "researcher_label": researcher,
                        "publisher": publisher,
                        "topic": topic,
                        "output_count": count,
                        "semantics": "DERIVED_FROM_MULTIPLE_STAGED_OUTPUTS_IDENTITY_UNRESOLVED",
                    }
                )
    return derived


class PolicyResearchStager:
    def __init__(self, connector: NkisResearchReportConnector) -> None:
        self.connector = connector
        self.policy = nkis_research_policy()

    def stage(self) -> dict[str, object]:
        require_policy(self.policy, PolicyAction.FETCH)
        document = self.connector.fetch(self.connector.discover()[0])
        outputs = self.connector.parse_outputs(document)
        return {
            "coverage": {
                "page_no": document.metadata.get("page_no"),
                "row_count": document.metadata.get("row_count"),
                "total_count": document.metadata.get("total_count"),
                "topic_derivation_scope": "STAGED_OUTPUTS_ONLY",
            },
            "outputs": [item.to_dict() for item in stage_outputs(outputs)],
            "repeated_topics": repeated_research_topics(outputs),
        }


def render_policy_research_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage NKIS research reports for review.")
    parser.add_argument("--title")
    parser.add_argument("--publisher")
    parser.add_argument("--publisher-code")
    parser.add_argument("--year-begin", type=int)
    parser.add_argument("--year-end", type=int)
    parser.add_argument("--page-no", type=int, default=1)
    parser.add_argument("--row-count", type=int, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    connector = NkisResearchReportConnector(
        page_no=args.page_no,
        row_count=args.row_count,
        title=args.title,
        publisher=args.publisher,
        publisher_code=args.publisher_code,
        year_begin=args.year_begin,
        year_end=args.year_end,
    )
    try:
        payload = PolicyResearchStager(connector).stage()
    except (MissingNkisApiKey, NkisApiError, PolicyDenied, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    print(render_policy_research_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
