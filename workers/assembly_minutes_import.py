from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.assembly_minutes import (
    PARSER_REVISION,
    AssemblyMinutesParseError,
    parse_minutes_packet,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_minutes_import import (
    ASSEMBLY_MINUTES_FEEDER,
    AssemblyMinutesCapture,
    AssemblyMinutesImportError,
    build_assembly_minutes_capture,
)


def extract_layout_pages(pdf_bytes: bytes) -> tuple[list[str], str]:
    """Layout-mode text layer per page plus the extractor identity.

    pypdf is an optional extra (`minutes-pdf`) used only by this human-assisted lane.
    """

    try:
        import pypdf
    except ImportError:  # pragma: no cover - depends on the optional extra
        raise AssemblyMinutesImportError(
            "minutes text-layer extraction requires the optional 'minutes-pdf' extra (pypdf)"
        ) from None
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    return pages, f"pypdf {pypdf.__version__} extract_text(extraction_mode=layout)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate (default) or persist one operator-supplied official National Assembly "
            "committee minutes PDF as ordered speaker-turn observations. Never fetches, never "
            "creates or links People, never publishes Claims."
        )
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--confirm-official-minutes-copy",
        action="store_true",
        help="Confirm the artifact is the exact official PDF_LINK_URL download for the packet.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write to the database. Without it nothing is written.",
    )
    return parser


def _load_capture(args: argparse.Namespace) -> AssemblyMinutesCapture:
    if not args.confirm_official_minutes_copy:
        raise AssemblyMinutesImportError("--confirm-official-minutes-copy is required")
    packet = parse_minutes_packet(json.loads(args.packet.read_text(encoding="utf-8")))
    artifact = args.artifact.read_bytes()
    pages, extractor = extract_layout_pages(artifact)
    return build_assembly_minutes_capture(
        packet, artifact_bytes=artifact, pages=pages, extractor=extractor
    )


def _safe_report(capture: AssemblyMinutesCapture) -> dict[str, object]:
    meeting = capture.packet.meeting
    categories: dict[str, int] = {}
    for turn in capture.parsed.turns:
        categories[turn.speaker_role_category] = categories.get(turn.speaker_role_category, 0) + 1
    return {
        "feeder": ASSEMBLY_MINUTES_FEEDER,
        "confer_num": meeting.confer_num,
        "meeting_title": meeting.title,
        "artifact_sha256": capture.packet.artifact_sha256,
        "parser_revision": PARSER_REVISION,
        "extractor": capture.extractor,
        "text_layer_sha256": capture.text_layer_sha256,
        "pdf_page_count": capture.parsed.pdf_page_count,
        "turns": len(capture.parsed.turns),
        "turns_by_role_category": dict(sorted(categories.items())),
        "appendix_lines_excluded": capture.parsed.appendix_line_count,
        "quote_text_retained": capture.policy.can_show_excerpt,
        "fulltext_retained": False,
        "person_materialization": False,
        "claim_publication": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        capture = _load_capture(args)
    except (
        AssemblyMinutesParseError,
        AssemblyMinutesImportError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

    if not args.commit:
        print(
            json.dumps(
                {"status": "DRY_RUN"} | _safe_report(capture),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.database_url:
        parser.error("--database-url is required with --commit")

    repository = SqlAlchemyRepository(args.database_url)
    run = repository.start_source_run(
        ASSEMBLY_MINUTES_FEEDER, capture.scope_key, metadata=capture.run_metadata
    )
    try:
        committed = repository.commit_source_page(
            run_id=run.id,
            policy=capture.policy,
            source=capture.source,
            snapshot=capture.snapshot,
            observations=capture.observations(run.id),
            cursor=capture.cursor,
            checkpoint_metadata=capture.checkpoint_metadata,
        )
        finished = repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    except (OSError, RuntimeError, SQLAlchemyError, ValueError) as exc:
        repository.finish_source_run(
            run.id,
            SourceRunStatus.FAILED,
            error_code="ASSEMBLY_MINUTES_IMPORT_FAILED",
            error_summary=type(exc).__name__,
        )
        raise

    print(
        json.dumps(
            {
                "status": "COMMITTED",
                **_safe_report(capture),
                "run_id": str(finished.id),
                "snapshot_id": str(committed.snapshot_id),
                "observations_created": committed.observations_created,
                "observations_unchanged": committed.observations_unchanged,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
