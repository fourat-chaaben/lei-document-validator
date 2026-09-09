#!/usr/bin/env python3
"""
XML/LEI Document Validator
==========================

Prueft XML-Dokumente mit Entitaetsdaten automatisch auf Vollstaendigkeit,
Formatkorrektheit und Konsistenz - und schreibt einen Report.

Hintergrund: In meiner Zeit bei der EQS Group habe ich solche Dokumente
manuell geprueft. Dieses Tool ist meine Antwort darauf: die immer gleiche
Pruefung als Skript, das per Cron automatisch laufen kann.

Verwendung:
    python validate_documents.py --input ./samples --report ./report.csv
    python validate_documents.py --input ./samples --report ./report.json --format json

Exit-Codes (wichtig fuer Automatisierung):
    0 = alle Dokumente gueltig
    1 = mindestens ein Fehler gefunden
    2 = Ausfuehrungsfehler (z.B. Ordner nicht gefunden)
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
    """Liest eine XML-Datei und gibt die Felder als Dictionary zurueck.

    Erwartete Struktur:
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
    """Wendet alle Regeln auf ein Dokument an und sammelt die Fehler."""
    errors = []
    for field, rule in FIELD_RULES.items():
        if field not in fields:
            errors.append(f"{field}: Feld fehlt im Dokument")
            continue
        problem = rule(fields[field])
        if problem:
            errors.append(f"{field}: {problem}")
    return errors


def find_duplicates(results: list) -> dict:
    """Findet LEIs, die in mehreren Dateien vorkommen.

    Duplikate sind ein klassischer Datenqualitaetsfehler: formal ist jede
    Datei korrekt, aber zusammen ergeben sie einen Widerspruch.
    """
    seen = defaultdict(list)
    for row in results:
        lei = row.get("lei")
        if lei:
            seen[lei].append(row["file"])
    return {lei: files for lei, files in seen.items() if len(files) > 1}


def run(input_dir: Path) -> list:
    """Prueft alle XML-Dateien im Ordner und gibt die Ergebnisse zurueck."""
    files = sorted(input_dir.glob("*.xml"))
    if not files:
        log.warning("Keine XML-Dateien in %s gefunden", input_dir)

    results = []
    for path in files:
        try:
            fields = parse_document(path)
            errors = validate_document(fields)
        except ET.ParseError as exc:
            fields, errors = {}, [f"XML nicht lesbar: {exc}"]

        results.append({
            "file": path.name,
            "lei": fields.get("lei", ""),
            "legalName": fields.get("legalName", ""),
            "status": "OK" if not errors else "FEHLER",
            "error_count": len(errors),
            "errors": "; ".join(errors),
        })
        log.info("%-24s %s", path.name, "OK" if not errors else f"{len(errors)} Fehler")

    # Duplikate nachtraeglich markieren
    for lei, dupe_files in find_duplicates(results).items():
        log.warning("Duplikat: LEI %s in %s", lei, ", ".join(dupe_files))
        for row in results:
            if row["lei"] == lei:
                row["status"] = "FEHLER"
                row["error_count"] += 1
                extra = f"lei: Duplikat (auch in {', '.join(f for f in dupe_files if f != row['file'])})"
                row["errors"] = f"{row['errors']}; {extra}" if row["errors"] else extra

    return results


def write_report(results: list, report_path: Path, fmt: str) -> None:
    """Schreibt den Report als CSV oder JSON."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        with report_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["file", "lei", "legalName", "status", "error_count", "errors"])
            writer.writeheader()
            writer.writerows(results)
    log.info("Report geschrieben: %s", report_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validiert XML-Dokumente mit LEI-Daten.")
    parser.add_argument("--input", required=True, type=Path, help="Ordner mit XML-Dateien")
    parser.add_argument("--report", default=Path("report.csv"), type=Path, help="Pfad fuer den Report")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Report-Format")
    args = parser.parse_args()

    if not args.input.is_dir():
        log.error("Ordner nicht gefunden: %s", args.input)
        return 2

    results = run(args.input)
    write_report(results, args.report, args.format)

    failed = sum(1 for r in results if r["status"] == "FEHLER")
    log.info("Ergebnis: %d Dokumente geprueft, %d fehlerhaft", len(results), failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
