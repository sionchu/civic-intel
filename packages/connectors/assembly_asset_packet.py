"""Human-reviewed National Assembly Gazette asset-disclosure packet (재산공개 국회공보).

The authority is the official 국회공보 재산변동사항/재산등록사항 공개 issue published by
국회공직자윤리위원회. The operator saves the exact Gazette PDF and transcribes selected
member tables into this packet; this module only validates the packet. It never fetches.

Privacy contract (AGENTS.md): member-level only (printed position must be 국회의원); no
family names, no 소재지/면적/권리의 명세, no account/parcel numbers, no change reasons.
Items held by reported relatives are accepted only as a coarse relation code plus values
so the printed member totals can be cross-checked; they are never persisted.
Amounts are the declared values printed in the Gazette (thousand KRW), not market wealth.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

ASSET_PACKET_SCHEMA = "assembly-asset-gazette-reviewed-packet.v1"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
HUMAN_REVIEWED = "HUMAN_REVIEWED"
ASSET_REVIEW_STATUSES = frozenset({REVIEW_REQUIRED, HUMAN_REVIEWED})
# robots.txt on www.assembly.go.kr is `Disallow: /` (re-observed 2026-10-05).
ASSET_AUTOMATION_GATE = "ASSEMBLY_GAZETTE_AUTOMATION_BLOCKED_ROBOTS"
GAZETTE_HOST = "www.assembly.go.kr"
GAZETTE_DETAIL_PATH = "/portal/cnts/cntsCont/dataA.do"
AMOUNT_UNIT = "THOUSAND_KRW"
VALUE_SEMANTICS = "DECLARED_VALUE_NOT_MARKET_WEALTH"
MEMBER_POSITION = "국회의원"

DISCLOSURE_KIND_REGULAR = "정기"
DISCLOSURE_KIND_OCCASIONAL = "수시"
DISCLOSURE_KINDS = frozenset({DISCLOSURE_KIND_REGULAR, DISCLOSURE_KIND_OCCASIONAL})
REPORT_CHANGE = "변동신고"
REPORT_INITIAL = "최초등록"
REPORT_REREGISTRATION = "재등록"
REPORT_RETIREMENT = "퇴직"
REGISTRATION_REPORT_TYPES = frozenset({REPORT_INITIAL, REPORT_REREGISTRATION})
REPORT_TYPES = frozenset({REPORT_CHANGE, REPORT_INITIAL, REPORT_REREGISTRATION, REPORT_RETIREMENT})
COVERAGE_SELECTED = "SELECTED_MEMBERS"
COVERAGE_FULL_ISSUE = "FULL_ISSUE"
COVERAGES = frozenset({COVERAGE_SELECTED, COVERAGE_FULL_ISSUE})

RELATION_SELF = "SELF"
# Coarse reviewer mapping of the printed 본인과의 관계; the printed kinship term is not kept.
HOLDER_RELATIONS = frozenset(
    {
        RELATION_SELF,
        "SPOUSE",
        "LINEAL_ASCENDANT",
        "LINEAL_DESCENDANT",
        "OTHER_REPORTED_RELATIVE",
    }
)
CATEGORY_DEBT = "DEBT"
# Statutory 재산의 구분 (공직자윤리법 제4조) as codes; the printed heading is kept verbatim.
ITEM_CATEGORIES = frozenset(
    {
        "LAND",
        "BUILDING",
        "REAL_RIGHT_OR_VEHICLE",
        "CASH",
        "DEPOSIT",
        "SECURITIES",
        "BOND_CLAIM",
        CATEGORY_DEBT,
        "GOLD_PLATINUM",
        "JEWELRY",
        "ANTIQUE_ART",
        "MEMBERSHIP",
        "INTELLECTUAL_PROPERTY",
        "PARTNERSHIP_EQUITY",
        "STOCK_OPTION",
        "VIRTUAL_ASSET",
        "NONPROFIT_CONTRIBUTION",
        "POLITICAL_FUND_DEPOSIT",
    }
)
# Coarsest location level kept: 시/도 only, from a closed list (no 시/군/구, no address).
REGIONS_SIDO = frozenset(
    {
        "서울특별시",
        "부산광역시",
        "대구광역시",
        "인천광역시",
        "광주광역시",
        "대전광역시",
        "울산광역시",
        "세종특별자치시",
        "경기도",
        "강원특별자치도",
        "충청북도",
        "충청남도",
        "전북특별자치도",
        "전라남도",
        "경상북도",
        "경상남도",
        "제주특별자치도",
        "해외",
    }
)
AMOUNT_FIELDS = ("prior_value", "increase", "decrease", "current_value")
# Net (assets minus debts) cross-check rule; UNVERIFIED until the first real packet.
CROSS_CHECKED_FIELDS = ("prior_value", "current_value")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISSUE = re.compile(r"^(\d{4})-(\d{1,4})$")
_PDF_ID = re.compile(r"^\d{1,12}$")
_MONA_CD = re.compile(r"^[0-9A-Z]{4,12}$")
_AMOUNT_TEXT = re.compile(r"^(-|△)?\s*(\d{1,3}(?:,\d{3})*|\d+)$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\d{2,4}[-.\s]\d{3,4}[-.\s]\d{4}")
_ACCOUNT_LIKE = re.compile(r"\d{2,6}-\d{2,6}-\d{2,8}|\d{10,}")
_ADDRESS_LIKE = re.compile(
    r"\d+\s*(?:번지|번길|동|호|층|리)(?![가-힣])"  # 12번지, 101동 1203호, 3층
    r"|[가-힣](?:로|길)\s*\d"  # 테헤란로 123, 무슨길 4
    r"|[가-힣](?:읍|면|리|동|가)\s+\d+(?:-\d+)?"  # 무슨동 12-3
    r"|\d+-\d+"  # 지번 12-3
    r"|㎡|m²|m2\b|제곱미터|평방미터"
    r"|(?:특별시|광역시|특별자치시|특별자치도|[가-힣]도)\s*[가-힣]+(?:시|군|구)"  # 시/도 + 시/군/구
)


class AssemblyAssetPacketError(ValueError):
    """A reviewed Assembly asset packet cannot be interpreted safely."""


def _exact_keys(payload: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise AssemblyAssetPacketError(f"{label} contains unsupported fields: {', '.join(unknown)}")


def _optional_text(value: object, field: str, *, max_length: int = 200) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AssemblyAssetPacketError(f"asset packet {field} must be text")
    text = value.strip()
    if not text:
        return None
    if len(text) > max_length:
        raise AssemblyAssetPacketError(f"asset packet {field} is too long")
    if _EMAIL.search(text) or _PHONE.search(text):
        raise AssemblyAssetPacketError(f"asset packet {field} must not contain contact details")
    return text


def _required_text(value: object, field: str, *, max_length: int = 200) -> str:
    text = _optional_text(value, field, max_length=max_length)
    if text is None:
        raise AssemblyAssetPacketError(f"asset packet lacks {field}")
    return text


def _private_safe_text(value: object, field: str, *, max_length: int = 60) -> str | None:
    """Short descriptive text that must carry no address-, parcel- or account-like detail."""

    text = _optional_text(value, field, max_length=max_length)
    if text is None:
        return None
    if _ACCOUNT_LIKE.search(text):
        raise AssemblyAssetPacketError(
            f"asset packet {field} must not contain account-like numbers"
        )
    if _ADDRESS_LIKE.search(text):
        raise AssemblyAssetPacketError(f"asset packet {field} must not contain address-like detail")
    return text


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AssemblyAssetPacketError(f"asset packet {field} must be a positive integer")
    return value


def _iso_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(_required_text(value, field))
    except ValueError:
        raise AssemblyAssetPacketError(f"asset packet {field} is invalid") from None


def _optional_iso_date(value: object, field: str) -> date | None:
    if value is None:
        return None
    return _iso_date(value, field)


@dataclass(frozen=True)
class DeclaredAmount:
    """A printed amount in thousand KRW: verbatim text plus the parsed integer."""

    text: str
    value: int

    @classmethod
    def from_mapping(cls, raw: object, field: str) -> DeclaredAmount | None:
        if raw is None:
            return None  # not printed: distinct from a printed zero
        if not isinstance(raw, Mapping):
            raise AssemblyAssetPacketError(f"asset packet {field} is malformed")
        _exact_keys(raw, {"text", "value"}, f"asset packet {field}")
        text = _required_text(raw.get("text"), f"{field}.text", max_length=24)
        value = raw.get("value")
        if isinstance(value, bool) or not isinstance(value, int):
            raise AssemblyAssetPacketError(f"asset packet {field}.value must be an integer")
        match = _AMOUNT_TEXT.fullmatch(text)
        if match is None:
            raise AssemblyAssetPacketError(
                f"asset packet {field}.text must be a plain printed amount"
            )
        sign, digits = match.groups()
        parsed = int(digits.replace(",", "")) * (-1 if sign else 1)
        if parsed != value:
            raise AssemblyAssetPacketError(f"asset packet {field}.value differs from its text")
        return cls(text=text, value=value)

    def normalized(self) -> dict[str, object]:
        return {"text": self.text, "value": self.value}


def _amounts(raw: Mapping[str, Any], label: str) -> dict[str, DeclaredAmount | None]:
    return {
        name: DeclaredAmount.from_mapping(raw.get(name), f"{label}.{name}")
        for name in AMOUNT_FIELDS
    }


def _normalized_amounts(amounts: Mapping[str, DeclaredAmount | None]) -> dict[str, object]:
    return {
        name: (amount.normalized() if amount is not None else None)
        for name, amount in amounts.items()
    }


@dataclass(frozen=True)
class GazetteLocator:
    page_number: int
    table_index: int
    table_row: int

    @classmethod
    def from_mapping(cls, raw: object, label: str) -> GazetteLocator:
        if not isinstance(raw, Mapping):
            raise AssemblyAssetPacketError(f"asset packet {label} is malformed")
        _exact_keys(raw, {"page_number", "table_index", "table_row"}, f"asset packet {label}")
        return cls(
            page_number=_positive_int(raw.get("page_number"), f"{label}.page_number"),
            table_index=_positive_int(raw.get("table_index"), f"{label}.table_index"),
            table_row=_positive_int(raw.get("table_row"), f"{label}.table_row"),
        )

    def normalized(self) -> dict[str, int]:
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "table_row": self.table_row,
        }


def _canonical_gazette_url(pdf_id: str) -> str:
    return (
        f"https://{GAZETTE_HOST}{GAZETTE_DETAIL_PATH}?cntsDivCd=NAMGZN&menuNo=601019"
        f"&pdfClsCd=CPR&pdfId={pdf_id}"
    )


@dataclass(frozen=True)
class GazetteSource:
    gazette_issue: str
    gazette_title: str
    publication_date: date
    disclosure_kind: str
    reporting_period_text: str
    reporting_period_start: date | None
    reporting_period_end: date | None
    pdf_id: str
    page_url: str
    artifact_filename: str
    artifact_sha256: str
    rights_mark: str | None
    automation_gate: str

    @property
    def canonical_url(self) -> str:
        return _canonical_gazette_url(self.pdf_id)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> GazetteSource:
        _exact_keys(
            raw,
            {
                "gazette_issue",
                "gazette_title",
                "publication_date",
                "disclosure_kind",
                "reporting_period_text",
                "reporting_period_start",
                "reporting_period_end",
                "pdf_id",
                "page_url",
                "artifact_filename",
                "artifact_sha256",
                "rights_mark",
                "automation_gate",
            },
            "asset packet source",
        )
        issue = _required_text(raw.get("gazette_issue"), "source.gazette_issue")
        issue_match = _ISSUE.fullmatch(issue)
        if issue_match is None:
            raise AssemblyAssetPacketError("asset packet gazette_issue must look like 2026-54")
        publication_date = _iso_date(raw.get("publication_date"), "source.publication_date")
        if int(issue_match.group(1)) != publication_date.year:
            raise AssemblyAssetPacketError(
                "asset packet gazette_issue year differs from publication_date"
            )
        kind = _required_text(raw.get("disclosure_kind"), "source.disclosure_kind")
        if kind not in DISCLOSURE_KINDS:
            raise AssemblyAssetPacketError("asset packet disclosure_kind is unsupported")
        start = _optional_iso_date(
            raw.get("reporting_period_start"), "source.reporting_period_start"
        )
        end = _optional_iso_date(raw.get("reporting_period_end"), "source.reporting_period_end")
        if start and end and start > end:
            raise AssemblyAssetPacketError("asset packet reporting period is inverted")
        if end and end > publication_date:
            raise AssemblyAssetPacketError("asset packet reporting period ends after publication")
        sha256 = _required_text(raw.get("artifact_sha256"), "source.artifact_sha256")
        if not _SHA256.fullmatch(sha256):
            raise AssemblyAssetPacketError("asset packet artifact_sha256 is invalid")
        pdf_id = _required_text(raw.get("pdf_id"), "source.pdf_id")
        if not _PDF_ID.fullmatch(pdf_id):
            raise AssemblyAssetPacketError("asset packet pdf_id must be digits")
        page_url = _required_text(raw.get("page_url"), "source.page_url", max_length=500)
        try:
            parsed = urlparse(page_url)
            port = parsed.port
        except ValueError:
            raise AssemblyAssetPacketError("asset packet page_url is invalid") from None
        if (
            parsed.scheme != "https"
            or parsed.hostname != GAZETTE_HOST
            or parsed.path != GAZETTE_DETAIL_PATH
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
            or "#" in page_url
            or parsed.params
        ):
            raise AssemblyAssetPacketError(
                "asset packet page_url must be the official https Gazette detail page"
            )
        query = parse_qs(parsed.query, keep_blank_values=True)
        expected_query = {
            "cntsDivCd": "NAMGZN",
            "menuNo": "601019",
            "pdfClsCd": "CPR",
            "pdfId": pdf_id,
        }
        if query.get("cntsDivCd") != ["NAMGZN"] or query.get("pdfId") != [pdf_id]:
            raise AssemblyAssetPacketError(
                "asset packet page_url does not match the Gazette pdf_id"
            )
        # Do not retain arbitrary caller query/fragment text in snapshot metadata. A
        # credential denylist misses alternate names (and values in unknown keys).
        if any(
            key not in expected_query or values != [expected_query[key]]
            for key, values in query.items()
        ):
            raise AssemblyAssetPacketError("asset packet page_url has unsupported query parameters")
        if (
            _required_text(raw.get("automation_gate"), "source.automation_gate")
            != ASSET_AUTOMATION_GATE
        ):
            raise AssemblyAssetPacketError(
                "asset packet automation gate is not the reviewed blocked state"
            )
        return cls(
            gazette_issue=issue,
            gazette_title=_required_text(raw.get("gazette_title"), "source.gazette_title"),
            publication_date=publication_date,
            disclosure_kind=kind,
            reporting_period_text=_required_text(
                raw.get("reporting_period_text"), "source.reporting_period_text", max_length=80
            ),
            reporting_period_start=start,
            reporting_period_end=end,
            pdf_id=pdf_id,
            page_url=_canonical_gazette_url(pdf_id),
            artifact_filename=_required_text(
                raw.get("artifact_filename"), "source.artifact_filename"
            ),
            artifact_sha256=sha256,
            rights_mark=_optional_text(raw.get("rights_mark"), "source.rights_mark"),
            automation_gate=ASSET_AUTOMATION_GATE,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "gazette_issue": self.gazette_issue,
            "gazette_title": self.gazette_title,
            "publication_date": self.publication_date.isoformat(),
            "disclosure_kind": self.disclosure_kind,
            "reporting_period_text": self.reporting_period_text,
            "reporting_period_start": (
                self.reporting_period_start.isoformat() if self.reporting_period_start else None
            ),
            "reporting_period_end": (
                self.reporting_period_end.isoformat() if self.reporting_period_end else None
            ),
            "pdf_id": self.pdf_id,
            "page_url": self.page_url,
            "artifact_filename": self.artifact_filename,
            "artifact_sha256": self.artifact_sha256,
            "rights_mark": self.rights_mark,
            "automation_gate": self.automation_gate,
        }


@dataclass(frozen=True)
class AssetItemRow:
    locator: GazetteLocator
    holder_relation: str
    item_category: str
    item_category_text: str | None
    item_kind: str | None
    region_sido: str | None
    amounts: Mapping[str, DeclaredAmount | None]

    @property
    def is_self_held(self) -> bool:
        return self.holder_relation == RELATION_SELF

    @classmethod
    def from_mapping(cls, raw: object, *, report_type: str) -> AssetItemRow:
        if not isinstance(raw, Mapping):
            raise AssemblyAssetPacketError("asset packet item is malformed")
        _exact_keys(
            raw,
            {
                "locator",
                "holder_relation",
                "item_category",
                "item_category_text",
                "item_kind",
                "region_sido",
                *AMOUNT_FIELDS,
            },
            "asset packet item",
        )
        relation = _required_text(raw.get("holder_relation"), "item.holder_relation")
        if relation not in HOLDER_RELATIONS:
            raise AssemblyAssetPacketError("asset packet item.holder_relation is unsupported")
        category = _required_text(raw.get("item_category"), "item.item_category")
        if category not in ITEM_CATEGORIES:
            raise AssemblyAssetPacketError("asset packet item.item_category is unsupported")
        category_text = _private_safe_text(raw.get("item_category_text"), "item.item_category_text")
        item_kind = _private_safe_text(raw.get("item_kind"), "item.item_kind", max_length=30)
        region = _optional_text(raw.get("region_sido"), "item.region_sido", max_length=20)
        if region is not None and region not in REGIONS_SIDO:
            raise AssemblyAssetPacketError(
                "asset packet item.region_sido must be a 시/도 name only"
            )
        if relation != RELATION_SELF and (
            category_text is not None or item_kind is not None or region is not None
        ):
            raise AssemblyAssetPacketError(
                "asset packet relative-held items carry only relation, category and amounts"
            )
        amounts = _amounts(raw, "item")
        _check_report_shape(amounts, report_type, "item")
        return cls(
            locator=GazetteLocator.from_mapping(raw.get("locator"), "item.locator"),
            holder_relation=relation,
            item_category=category,
            item_category_text=category_text,
            item_kind=item_kind,
            region_sido=region,
            amounts=amounts,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "locator": self.locator.normalized(),
            "holder_relation": self.holder_relation,
            "item_category": self.item_category,
            "item_category_text": self.item_category_text,
            "item_kind": self.item_kind,
            "region_sido": self.region_sido,
            "amounts": _normalized_amounts(self.amounts),
        }


def _check_report_shape(
    amounts: Mapping[str, DeclaredAmount | None], report_type: str, label: str
) -> None:
    if amounts["current_value"] is None:
        raise AssemblyAssetPacketError(f"asset packet {label}.current_value is required")
    if report_type in REGISTRATION_REPORT_TYPES and any(
        amounts[name] is not None for name in ("prior_value", "increase", "decrease")
    ):
        raise AssemblyAssetPacketError(
            f"asset packet {label} registration reports carry only current_value"
        )


@dataclass(frozen=True)
class MemberDisclosure:
    printed_member_name: str
    printed_affiliation: str | None
    printed_position: str
    reviewer_stated_mona_cd: str | None
    mona_cd_basis: str | None
    report_type: str
    total_locator: GazetteLocator
    declared_totals: Mapping[str, DeclaredAmount | None]
    items: tuple[AssetItemRow, ...]

    @classmethod
    def from_mapping(cls, raw: object, *, disclosure_kind: str) -> MemberDisclosure:
        if not isinstance(raw, Mapping):
            raise AssemblyAssetPacketError("asset packet member is malformed")
        _exact_keys(
            raw,
            {
                "printed_member_name",
                "printed_affiliation",
                "printed_position",
                "reviewer_stated_mona_cd",
                "mona_cd_basis",
                "report_type",
                "total_locator",
                "declared_totals",
                "items",
            },
            "asset packet member",
        )
        name = _private_safe_text(
            raw.get("printed_member_name"), "member.printed_member_name", max_length=30
        )
        if name is None or re.search(r"\d", name):
            raise AssemblyAssetPacketError("asset packet member.printed_member_name is invalid")
        position = _required_text(raw.get("printed_position"), "member.printed_position")
        if position != MEMBER_POSITION:
            raise AssemblyAssetPacketError(
                "asset packet is member-level only: printed_position must be 국회의원"
            )
        report_type = _required_text(raw.get("report_type"), "member.report_type")
        if report_type not in REPORT_TYPES:
            raise AssemblyAssetPacketError("asset packet member.report_type is unsupported")
        if disclosure_kind == DISCLOSURE_KIND_REGULAR and report_type != REPORT_CHANGE:
            raise AssemblyAssetPacketError("asset packet 정기 issues carry only 변동신고 members")
        mona_cd = _optional_text(
            raw.get("reviewer_stated_mona_cd"), "member.reviewer_stated_mona_cd"
        )
        basis = _optional_text(raw.get("mona_cd_basis"), "member.mona_cd_basis")
        if mona_cd is not None and not _MONA_CD.fullmatch(mona_cd):
            raise AssemblyAssetPacketError("asset packet member.reviewer_stated_mona_cd is invalid")
        if (mona_cd is None) != (basis is None):
            raise AssemblyAssetPacketError(
                "asset packet member MONA_CD and its mona_cd_basis must be stated together"
            )
        totals_raw = raw.get("declared_totals")
        if not isinstance(totals_raw, Mapping):
            raise AssemblyAssetPacketError("asset packet member.declared_totals is malformed")
        _exact_keys(totals_raw, set(AMOUNT_FIELDS), "asset packet member.declared_totals")
        totals = _amounts(totals_raw, "member.declared_totals")
        _check_report_shape(totals, report_type, "member.declared_totals")
        items_raw = raw.get("items")
        if not isinstance(items_raw, list) or not items_raw:
            raise AssemblyAssetPacketError("asset packet member.items must be a non-empty list")
        items = tuple(
            AssetItemRow.from_mapping(item, report_type=report_type) for item in items_raw
        )
        member = cls(
            printed_member_name=name,
            printed_affiliation=_private_safe_text(
                raw.get("printed_affiliation"), "member.printed_affiliation"
            ),
            printed_position=position,
            reviewer_stated_mona_cd=mona_cd,
            mona_cd_basis=basis,
            report_type=report_type,
            total_locator=GazetteLocator.from_mapping(
                raw.get("total_locator"), "member.total_locator"
            ),
            declared_totals=totals,
            items=items,
        )
        member.cross_check_totals()
        return member

    def cross_check_totals(self) -> None:
        """Printed prior/current totals must equal the signed item sum (debts subtract).

        Increase/decrease totals are kept verbatim but not cross-checked: how the Gazette
        nets debt increases/decreases into the member total is not yet confirmed.
        """

        for name in CROSS_CHECKED_FIELDS:
            declared = self.declared_totals[name]
            if declared is None:
                continue
            total = 0
            for item in self.items:
                amount = item.amounts[name]
                if amount is None:
                    raise AssemblyAssetPacketError(
                        f"asset packet member total {name} cannot be cross-checked: an item lacks it"
                    )
                total += -amount.value if item.item_category == CATEGORY_DEBT else amount.value
            if total != declared.value:
                raise AssemblyAssetPacketError(
                    f"asset packet member {name} items ({total}) differ from declared total "
                    f"({declared.value})"
                )

    def normalized(self) -> dict[str, object]:
        return {
            "printed_member_name": self.printed_member_name,
            "printed_affiliation": self.printed_affiliation,
            "printed_position": self.printed_position,
            "reviewer_stated_mona_cd": self.reviewer_stated_mona_cd,
            "mona_cd_basis": self.mona_cd_basis,
            "report_type": self.report_type,
            "total_locator": self.total_locator.normalized(),
            "declared_totals": _normalized_amounts(self.declared_totals),
            "items": [item.normalized() for item in self.items],
        }


@dataclass(frozen=True)
class ReviewedAssemblyAssetPacket:
    review_status: str
    coverage: str
    source: GazetteSource
    members: tuple[MemberDisclosure, ...]

    def normalized(self) -> dict[str, object]:
        return {
            "schema": ASSET_PACKET_SCHEMA,
            "review_status": self.review_status,
            "coverage": self.coverage,
            "declared_member_count": len(self.members),
            "source": self.source.normalized(),
            "members": [member.normalized() for member in self.members],
        }

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(
            self.normalized(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def is_human_reviewed(self) -> bool:
        return self.review_status == HUMAN_REVIEWED

    @property
    def scope_key(self) -> str:
        return f"gazette:{self.source.gazette_issue}:pdf:{self.source.pdf_id}"

    def record_key(self, locator: GazetteLocator) -> str:
        """Snapshot-scoped observation key: issue + exact Gazette locator; never a name."""

        return (
            f"{self.source.gazette_issue}:p{locator.page_number}:"
            f"t{locator.table_index}:r{locator.table_row}"
        )


def parse_reviewed_assembly_asset_packet(raw: Mapping[str, Any]) -> ReviewedAssemblyAssetPacket:
    _exact_keys(
        raw,
        {"schema", "review_status", "coverage", "declared_member_count", "source", "members"},
        "asset packet",
    )
    if raw.get("schema") != ASSET_PACKET_SCHEMA:
        raise AssemblyAssetPacketError("asset packet schema is unsupported")
    status = raw.get("review_status")
    if status not in ASSET_REVIEW_STATUSES:
        raise AssemblyAssetPacketError("asset packet review_status is unsupported")
    coverage = raw.get("coverage")
    if coverage not in COVERAGES:
        raise AssemblyAssetPacketError("asset packet coverage is unsupported")
    source_raw = raw.get("source")
    members_raw = raw.get("members")
    if not isinstance(source_raw, Mapping) or not isinstance(members_raw, list) or not members_raw:
        raise AssemblyAssetPacketError("asset packet source/members are malformed")
    source = GazetteSource.from_mapping(source_raw)
    members = tuple(
        MemberDisclosure.from_mapping(item, disclosure_kind=source.disclosure_kind)
        for item in members_raw
    )
    declared_count = raw.get("declared_member_count")
    if isinstance(declared_count, bool) or declared_count != len(members):
        raise AssemblyAssetPacketError("asset packet declared_member_count differs from members")
    locators = [member.total_locator for member in members] + [
        item.locator for member in members for item in member.items
    ]
    if len(set(locators)) != len(locators):
        raise AssemblyAssetPacketError("asset packet Gazette locators must be unique")
    codes = [m.reviewer_stated_mona_cd for m in members if m.reviewer_stated_mona_cd]
    if len(set(codes)) != len(codes):
        raise AssemblyAssetPacketError("asset packet repeats a reviewer-stated MONA_CD")
    return ReviewedAssemblyAssetPacket(
        review_status=str(status),
        coverage=str(coverage),
        source=source,
        members=members,
    )
