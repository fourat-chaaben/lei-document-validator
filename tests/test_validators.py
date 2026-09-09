"""Tests fuer die Validierungsregeln.

Ausfuehren mit:  python -m pytest tests/ -v
(oder ohne pytest:  python tests/test_validators.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from validators import (  # noqa: E402
    lei_checksum_valid,
    validate_country,
    validate_date,
    validate_enum,
    validate_lei,
    validate_required,
)

VALID_LEI = "529900T8BM49AURSDO55"


def test_valid_lei_passes():
    assert validate_lei(VALID_LEI) is None
    assert lei_checksum_valid(VALID_LEI) is True


def test_wrong_checksum_fails():
    assert "Pruefziffer" in validate_lei("529900T8BM49AURSDO99")


def test_too_short_fails():
    assert "20 Zeichen" in validate_lei("529900T8BM49")


def test_empty_lei_fails():
    assert validate_lei("") == "LEI fehlt"


def test_lowercase_is_accepted():
    # Wir normalisieren auf Grossbuchstaben, daher gueltig
    assert validate_lei(VALID_LEI.lower()) is None


def test_required_field():
    assert validate_required("Muster GmbH") is None
    assert validate_required("   ") == "Pflichtfeld ist leer"


def test_date_rules():
    assert validate_date("2021-04-19") is None
    assert "Format" in validate_date("19.04.2021")
    assert "Zukunft" in validate_date("2099-01-01")


def test_country_rules():
    assert validate_country("DE") is None
    assert validate_country("de") is None
    assert "ungueltig" in validate_country("XX1")


def test_enum_rules():
    allowed = {"ACTIVE", "INACTIVE"}
    assert validate_enum("active", allowed) is None
    assert "nicht erlaubt" in validate_enum("UNKNOWN", allowed)


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
                passed += 1
            except AssertionError as exc:
                print(f"FAIL  {name}: {exc}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
