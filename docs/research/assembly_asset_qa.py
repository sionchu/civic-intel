"""Finite, opt-in research QA. No Civic Intel imports, DB writes, or raw-data files.

Run with the bundled analysis Python (openpyxl is read-only here). Public workbook
bytes exist only in memory. Output contains aggregate counts and source references.
This is not a connector, identity resolver, completeness proof, or runtime dependency.
"""

import argparse
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from zipfile import BadZipFile

import openpyxl

CATALOG_REVISION = "a03999074636191dfe86d299567b918fd85cf14a"
CATALOG_URL = (
    "https://raw.githubusercontent.com/opengirok/congress_asset_disclosure/"
    + CATALOG_REVISION + "/README.md"
)
OPENWATCH_SHEETS = {
    "openwatch-members": "1OXS5Mgf1Z7xLiqBVppCCduPRVoXVj5P_JI4YXWghRLk",
    "openwatch-2024-03": "1EvHrznK6SwcBrngOapY9l5hF3xmzYqRAYQ0inQXqSyw",
    "openwatch-2025-03": "1TKNm4vrLI1_dXZiK1HcqWMRasemN14ojTwABWbM54JA",
    "openwatch-2026-03": "1ntYbYitd9jHEY_MTJNj5V2R_S9iI4Rbw6fZoMOKMsiM",
}


def fetch(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def compact(value):
    return re.sub(r"\s+", "", "" if value is None else str(value))


def read_tables(content):
    workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    tables = []
    for sheet in workbook:
        rows = list(sheet.iter_rows(values_only=True))
        header_index = next((i for i, row in enumerate(rows[:25])
                             if {"이름", "성명"} & {compact(v) for v in row}), None)
        if header_index is None:
            tables.append((sheet.title, None, [], None))
            continue
        headers = [compact(v) or f"unnamed_{i}" for i, v in enumerate(rows[header_index])]
        name_col = next(k for k in headers if k in {"이름", "성명"})
        records = [dict(zip(headers, row, strict=False)) for row in rows[header_index + 1:]]
        records = [r for r in records if compact(r.get(name_col)) not in {"", "이름", "성명"}]
        tables.append((sheet.title, headers, records, header_index + 1))
    workbook.close()
    return tables


def summarize(table, crosswalk):
    title, headers, records, header_row = table
    if headers is None:
        return {"tab": title, "status": "no_name_header_in_first_25_rows"}
    name_key = next(k for k in headers if k in {"이름", "성명"})
    hashes = Counter(hashlib.sha256(json.dumps(r, ensure_ascii=False, sort_keys=True,
                     default=str).encode()).hexdigest() for r in records)
    content_rows = [json.dumps({k: v for k, v in r.items()
                    if not re.fullmatch(r"(?i)no|연번|번호", k)},
                    ensure_ascii=False, sort_keys=True, default=str) for r in records]
    content_hashes = Counter(hashlib.sha256(r.encode()).hexdigest() for r in content_rows)
    # Only exact typed IDs are compared. Names count source groups, never link Persons.
    codes = [compact(r.get("monaCode")) for r in records]
    has_code = [c for c in codes if c]
    group_keys = {(compact(r.get("구분")), compact(r.get("소속")),
                   compact(r.get("직위")), compact(r.get(name_key))) for r in records}
    item_count = Counter((compact(r.get("구분")), compact(r.get("소속")),
                          compact(r.get("직위")), compact(r.get(name_key))) for r in records)
    excluded = sum("국회의원" not in compact(r.get("구분"))
                   and "국회의원" not in compact(r.get("직위"))
                   and "국회의장" not in compact(r.get("직위"))
                   and "국회부의장" not in compact(r.get("직위")) for r in records)
    duplicates = sum(n - 1 for n in hashes.values())
    id_fields = [h for h in headers if re.search(r"(?i)id|code|코드|^no$|연번|번호", h)]
    return {
        "tab": title, "header_row": header_row, "fields": headers,
        "rows_with_name": len(records), "exact_duplicate_excess": duplicates,
        "exact_duplicate_rate": duplicates / len(records) if records else None,
        "duplicate_excess_excluding_ordinal": sum(n - 1 for n in content_hashes.values()),
        "ordered_content_sha256_excluding_ordinal": hashlib.sha256(
            "\n".join(content_rows).encode()).hexdigest(),
        "source_name_role_groups_not_identities": len(group_keys),
        "rows_per_name_role_group_min_max": [min(item_count.values()), max(item_count.values())]
        if item_count else None,
        "rows_without_member_role_marker": excluded,
        "missing_fields": {h: sum(compact(r.get(h)) == "" for r in records) for h in headers},
        "identifier_columns": id_fields,
        "identifier_unique_nonblank": {h: len({compact(r.get(h)) for r in records
                                               if compact(r.get(h))}) for h in id_fields},
        "mona_code_nonblank_rows": len(has_code),
        "mona_code_in_crosswalk_rows": sum(c in crosswalk for c in has_code),
        "mona_code_distinct": len(set(has_code)),
        "mona_codes_absent_from_crosswalk_count": len(set(has_code) - set(crosswalk)),
        "period_counts": dict(Counter(compact(r.get("연월")) for r in records))
        if "연월" in headers else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-opengirok", action="store_true")
    args = parser.parse_args()
    sources = dict(OPENWATCH_SHEETS)
    if args.include_opengirok:
        catalog = fetch(CATALOG_URL).decode("utf-8")
        for heading, body in re.findall(r"## ([^\n]+)\n(.*?)(?=\n## |\Z)", catalog, re.DOTALL):
            match = re.search(r"docs.google.com/spreadsheets/d/([A-Za-z0-9_-]+)", body)
            if match:
                sources["opengirok-" + heading.strip()] = match[1]
    crosswalk = defaultdict(set)
    failed = False
    for label, sheet_id in sources.items():
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        try:
            content = fetch(url)
            tables = read_tables(content)
            if label == "openwatch-members":
                for _, headers, records, _ in tables:
                    if headers and "monaCode" in headers:
                        for row in records:
                            code = compact(row.get("monaCode"))
                            if code:
                                crosswalk[code].add(compact(row.get("hjId")))
            report = {
                "dataset": label, "source_url": url,
                "fetched_at": datetime.now(UTC).isoformat(),
                "xlsx_sha256": hashlib.sha256(content).hexdigest(),
                "tabs": [summarize(t, crosswalk) for t in tables],
            }
            if label == "openwatch-members":
                report["mona_codes_with_multiple_nonblank_hj_ids"] = sum(
                    len(ids - {""}) > 1 for ids in crosswalk.values())
            print(json.dumps(report, ensure_ascii=False), flush=True)
        except (OSError, ValueError, BadZipFile, openpyxl.utils.exceptions.InvalidFileException) as exc:
            failed = True
            print(json.dumps({"dataset": label, "error_type": type(exc).__name__}), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
