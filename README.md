# XML/LEI Document Validator

Automated quality checks for XML documents containing LEI data (Legal Entity Identifier, ISO 17442), including checksum validation, field rules, duplicate detection and reporting.

## The problem

During two years at EQS Group I checked XML documents and LEI data by hand: required fields, formats, consistency, document by document. The checks were always the same, only the data changed.

That repetition is what started this project. I wanted to know how to automate such a check properly instead of repeating it.

## What the tool does

```
XML files  →  parsing  →  rule checks  →  duplicate check  →  report (CSV/JSON)
```

- **LEI validation** per ISO 17442, including the mod-97-10 check digits (ISO 7064), so it catches not only malformed codes but also typos in codes that look correct
- **Field rules:** required fields, date format and plausibility (no future dates), ISO 3166 country codes, allowed status values
- **Duplicate detection** across all files: each file valid on its own, but contradictory together
- **Report** as CSV or JSON, with an error count and a concrete description per document
- **Exit codes** for automation: `0` = all clean, `1` = errors found, `2` = execution error

## Usage

```bash
python src/validate_documents.py --input ./samples --report ./report.csv
python src/validate_documents.py --input ./samples --report ./report.json --format json
```

Example output:

```
[INFO] entity_001.xml           OK
[INFO] entity_003_badchecksum.xml 1 error
[INFO] entity_004_missing.xml   5 errors
[WARNING] Duplicate: LEI 529900T8BM49AURSDO55 in entity_001.xml, entity_005_duplicate.xml
[INFO] Result: 5 documents checked, 4 with errors
```

Report (excerpt):

| file | lei | status | error_count | errors |
|---|---|---|---|---|
| entity_002.xml | 5493001KJTIIGC8Y1R12 | OK | 0 | |
| entity_003_badchecksum.xml | 529900T8BM49AURSDO99 | ERROR | 1 | lei: LEI check digits invalid (mod-97-10) |
| entity_004_missing.xml | | ERROR | 5 | lei: LEI missing; legalName: required field is empty; ... |

## Scheduling with Cron

To run the check without manual triggering, the script is scheduled:

```bash
# crontab -e
# Every weekday at 6:30 check all incoming documents
30 6 * * 1-5 /usr/bin/python3 /opt/lei-validator/src/validate_documents.py \
    --input /data/incoming --report /data/reports/$(date +\%F).csv >> /var/log/lei-validator.log 2>&1
```

The exit code makes the script usable in pipelines: on `1`, a follow-up step can raise an alert instead of passing faulty data downstream.

## How the LEI check digits work

An LEI has 20 characters; the last two are check digits. Validation per ISO 7064 (mod-97-10):

1. Convert letters to numbers (A=10, B=11, … Z=35), turning the alphanumeric code into one long number
2. Take that number modulo 97
3. The result must be **1**, otherwise the code is invalid

This catches typos and transposed digits that a pure format check (length, allowed characters) would miss.

## Tests

```bash
python tests/test_validators.py       # 9 tests, no external dependencies
python -m pytest tests/ -v            # or with pytest
```

## Project structure

```
├── src/
│   ├── validators.py           # validation rules (one testable function per rule)
│   └── validate_documents.py   # CLI: read files, validate, write report
├── tests/
│   └── test_validators.py      # unit tests for the rules
├── samples/                    # example documents (valid + deliberately broken)
└── README.md
```

## Design decisions

- **Rules as individual functions:** each rule returns `None` (ok) or an error message. This makes them testable in isolation and freely composable; adding a new field only requires one more entry in the rule set.
- **Standard library only:** no `pip install` needed, so the script runs on any system with Python 3, which is convenient for cron jobs on servers.
- **Collect errors instead of aborting:** a document is validated completely, so the report shows all problems at once instead of stopping at the first one.

## Stack

Python 3 (standard library: `xml.etree.ElementTree`, `csv`, `json`, `re`, `argparse`, `logging`, `pathlib`), Cron

---

**Fourat Chaaben** · [GitHub](https://github.com/fourat-chaaben) · [LinkedIn](https://linkedin.com/in/fourat-chaaben)
