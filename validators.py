"""
Validierungsregeln fuer LEI- und XML-Dokumentdaten.

Kernidee: Jede Regel ist eine kleine, testbare Funktion, die entweder
None (alles ok) oder eine Fehlermeldung als String zurueckgibt.
So kann man Regeln beliebig kombinieren und einzeln testen.
"""

import re
from datetime import datetime

# ---------------------------------------------------------------------------
# LEI (Legal Entity Identifier, ISO 17442)
# ---------------------------------------------------------------------------
# Aufbau: 20 Zeichen.
#   Stelle 1-4   : LOU-Praefix (vergebende Stelle)
#   Stelle 5-6   : immer "00" (reserviert)
#   Stelle 7-18  : Entitaets-Teil (alphanumerisch)
#   Stelle 19-20 : Pruefziffern (mod-97-10 nach ISO 7064)

LEI_PATTERN = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def _to_numeric(text: str) -> str:
    """Buchstaben in Zahlen umwandeln: A=10, B=11, ... Z=35.

    Das ist der ISO-7064-Trick: Aus dem alphanumerischen Code wird eine
    (sehr lange) reine Zahl, mit der man rechnen kann.
    """
    out = []
    for char in text:
        if char.isdigit():
            out.append(char)
        else:
            out.append(str(ord(char) - ord("A") + 10))
    return "".join(out)


def lei_checksum_valid(lei: str) -> bool:
    """Prueft die mod-97-10 Pruefziffer eines LEI.

    Verfahren: kompletten Code (inkl. Pruefziffern) in Zahlen wandeln
    und modulo 97 rechnen. Ergebnis muss 1 sein.
    """
    if not LEI_PATTERN.match(lei):
        return False
    return int(_to_numeric(lei)) % 97 == 1


def validate_lei(value):
    """Regel: Feld muss ein formal und rechnerisch gueltiger LEI sein."""
    if not value:
        return "LEI fehlt"
    lei = value.strip().upper()
    if len(lei) != 20:
        return f"LEI muss 20 Zeichen haben, hat {len(lei)}"
    if not LEI_PATTERN.match(lei):
        return "LEI-Format ungueltig (erwartet: 18 alphanumerische + 2 Ziffern)"
    if not lei_checksum_valid(lei):
        return "LEI-Pruefziffer falsch (mod-97-10)"
    return None


# ---------------------------------------------------------------------------
# Allgemeine Feldregeln
# ---------------------------------------------------------------------------

def validate_required(value):
    """Regel: Pflichtfeld darf nicht leer sein."""
    if value is None or str(value).strip() == "":
        return "Pflichtfeld ist leer"
    return None


def validate_date(value, fmt="%Y-%m-%d"):
    """Regel: Datum muss dem Format entsprechen und darf nicht in der Zukunft liegen."""
    if not value:
        return "Datum fehlt"
    try:
        parsed = datetime.strptime(value.strip(), fmt)
    except ValueError:
        return f"Datum '{value}' entspricht nicht dem Format {fmt}"
    if parsed > datetime.now():
        return f"Datum '{value}' liegt in der Zukunft"
    return None


def validate_country(value):
    """Regel: ISO-3166-Laendercode, zwei Grossbuchstaben."""
    if not value:
        return "Laendercode fehlt"
    if not re.match(r"^[A-Z]{2}$", value.strip().upper()):
        return f"Laendercode '{value}' ungueltig (erwartet 2 Buchstaben, z.B. DE)"
    return None


def validate_enum(value, allowed):
    """Regel: Wert muss aus einer erlaubten Liste stammen."""
    if not value:
        return "Wert fehlt"
    if value.strip().upper() not in allowed:
        return f"Wert '{value}' nicht erlaubt (erlaubt: {', '.join(sorted(allowed))})"
    return None


# ---------------------------------------------------------------------------
# Regelwerk: welches Feld wird wie geprueft
# ---------------------------------------------------------------------------

STATUS_VALUES = {"ACTIVE", "INACTIVE", "PENDING"}

FIELD_RULES = {
    "lei": validate_lei,
    "legalName": validate_required,
    "country": validate_country,
    "registrationDate": validate_date,
    "status": lambda v: validate_enum(v, STATUS_VALUES),
}
