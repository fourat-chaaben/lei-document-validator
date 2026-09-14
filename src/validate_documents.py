#!/usr/bin/env python3
"""
XML/LEI Document Validator
==========================

Automatically checks XML documents containing entity data for completeness,
format correctness and consistency, and writes a report.

Background: at EQS Group I ran these checks by hand. This tool is my answer
to that: the same repetitive check as a script that can run via Cron.

Usage:
    python validate_documents.py --input ./samples --report ./report.csv
    python validate_documents.py --input ./samples --report ./report.json --format json

Exit codes (relevant for automation):
    0 = all documents valid
    1 = at least one error found
    2 = execution error (e.g. directory not found)
"""

import argparse
import csv
import json
import logging
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from validators import FIELD_RULES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("validator")


def parse_document(path: Path) -> dict:
    """Read an XML file and return its fields as a dictionary.

    Expected structure:
        <entity>
            <lei>...</lei>
            <legalName>...</legalName>
            ...
        </entity>
    """
    tree = ET.parse(path)
    root = tree.getroot()
    return {child.tag: (child.text or "").strip() for child in root}


def validate_document(fields: dict) -> list:
    """Apply all rules to one document and collect the errors."""
    errors = []
    for field, rule in FIELD_RULES.items():
        if field not in fields:
            errors.append(f"{field}: field missing in document")
            continue
        problem = rule(fields[field])
        if problem:
            errors.append(f"{field}: {problem}")
    return errors


def find_duplicates(results: list) -> dict:
    """Find LEIs that appear in more than one file.

    Duplicates are a classic data quality issue: each file is valid on its
    own, but together they contradict each other.
    """
    seen = defaultdict(list)
    for row in results:
        lei = row.get("lei")
        if lei:
            seen[lei].append(row["file"])
    return {lei: files for lei, files in seen.items() if len(files) > 1}


def run(input_dir: Path) -> list:
    """Validate all XML files in the directory and return the results."""
    files = sorted(input_dir.glob("*.xml"))
    if not files:
        log.warning("No XML files found in %s", input_dir)

    results = []
    for path in files:
        try:
            fields = parse_document(path)
            errors = validate_document(fields)
        except ET.ParseError as exc:
            fields, errors = {}, [f"XML not readable: {exc}"]

        results.append({
            "file": path.name,
            "lei": fields.get("lei", ""),
            "legalName": fields.get("legalName", ""),
            "status": "OK" if not errors else "ERROR",
            "error_count": len(errors),
            "errors": "; ".join(errors),
        })
        log.info("%-26s %s", path.name, "OK" if not errors else f"{len(errors)} error(s)")

    # mark duplicates afterwards
    for lei, dupe_files in find_duplicates(results).items():
        log.warning("Duplicate: LEI %s in %s", lei, ", ".join(dupe_files))
        for row in results:
            if row["lei"] == lei:
                row["status"] = "ERROR"
                row["error_count"] += 1
                others = ", ".join(f for f in dupe_files if f != row["file"])
                extra = f"lei: duplicate (also in {others})"
                row["errors"] = f"{row['errors']}; {extra}" if row["errors"] else extra

    return results


def write_report(results: list, report_path: Path, fmt: str) -> None:
    """Write the report as CSV or JSON."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        with report_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["file", "lei", "legalName", "status", "error_count", "errors"])
            writer.writeheader()
            writer.writerows(results)
    log.info("Report written: %s", report_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validates XML documents containing LEI data.")
    parser.add_argument("--input", required=True, type=Path, help="directory containing XML files")
    parser.add_argument("--report", default=Path("report.csv"), type=Path, help="path for the report")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="report format")
    args = parser.parse_args()

    if not args.input.is_dir():
        log.error("Directory not found: %s", args.input)
        return 2

    results = run(args.input)
    write_report(results, args.report, args.format)

    failed = sum(1 for r in results if r["status"] == "ERROR")
    log.info("Result: %d documents checked, %d with errors", len(results), failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
