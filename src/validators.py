"""
Validation rules for LEI and XML document data.

Core idea: every rule is a small, testable function that returns either
None (all good) or an error message as a string. This makes rules easy to
combine and to test in isolation.
"""

import re
from datetime import datetime

# ---------------------------------------------------------------------------
# LEI (Legal Entity Identifier, ISO 17442)
# ---------------------------------------------------------------------------
# Structure: 20 characters.
#   pos 1-4   : LOU prefix (issuing organisation)
#   pos 5-6   : always "00" (reserved)
#   pos 7-18  : entity part (alphanumeric)
#   pos 19-20 : check digits (mod-97-10 per ISO 7064)

LEI_PATTERN = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def _to_numeric(text: str) -> str:
    """Convert letters to numbers: A=10, B=11, ... Z=35.

    This is the ISO 7064 trick: the alphanumeric code becomes one (very long)
    plain number we can do arithmetic on.
    """
    out = []
    for char in text:
        if char.isdigit():
            out.append(char)
        else:
            out.append(str(ord(char) - ord("A") + 10))
    return "".join(out)


def lei_checksum_valid(lei: str) -> bool:
    """Check the mod-97-10 check digits of an LEI.

    Method: convert the full code (including check digits) to numbers and
    take it modulo 97. The result must be 1.
    """
    if not LEI_PATTERN.match(lei):
        return False
    return int(_to_numeric(lei)) % 97 == 1


def validate_lei(value):
    """Rule: field must be a structurally and arithmetically valid LEI."""
    if not value:
        return "LEI missing"
    lei = value.strip().upper()
    if len(lei) != 20:
        return f"LEI must be 20 characters, got {len(lei)}"
    if not LEI_PATTERN.match(lei):
        return "LEI format invalid (expected 18 alphanumeric + 2 digits)"
    if not lei_checksum_valid(lei):
        return "LEI check digits invalid (mod-97-10)"
    return None


# ---------------------------------------------------------------------------
# General field rules
# ---------------------------------------------------------------------------

def validate_required(value):
    """Rule: required field must not be empty."""
    if value is None or str(value).strip() == "":
        return "required field is empty"
    return None


def validate_date(value, fmt="%Y-%m-%d"):
    """Rule: date must match the format and must not be in the future."""
    if not value:
        return "date missing"
    try:
        parsed = datetime.strptime(value.strip(), fmt)
    except ValueError:
        return f"date '{value}' does not match format {fmt}"
    if parsed > datetime.now():
        return f"date '{value}' is in the future"
    return None


def validate_country(value):
    """Rule: ISO 3166 country code, two uppercase letters."""
    if not value:
        return "country code missing"
    if not re.match(r"^[A-Z]{2}$", value.strip().upper()):
        return f"country code '{value}' invalid (expected 2 letters, e.g. DE)"
    return None


def validate_enum(value, allowed):
    """Rule: value must come from an allowed set."""
    if not value:
        return "value missing"
    if value.strip().upper() not in allowed:
        return f"value '{value}' not allowed (allowed: {', '.join(sorted(allowed))})"
    return None


# ---------------------------------------------------------------------------
# Rule set: which field is checked how
# ---------------------------------------------------------------------------

STATUS_VALUES = {"ACTIVE", "INACTIVE", "PENDING"}

FIELD_RULES = {
    "lei": validate_lei,
    "legalName": validate_required,
    "country": validate_country,
    "registrationDate": validate_date,
    "status": lambda v: validate_enum(v, STATUS_VALUES),
}
