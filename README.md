# XML/LEI Document Validator

Automatisierte Qualitätsprüfung von XML-Dokumenten mit LEI-Daten (Legal Entity Identifier, ISO 17442) — inklusive Prüfziffernvalidierung, Feldregeln, Duplikaterkennung und Report.

## Das Problem

In meiner Zeit bei der EQS Group habe ich zwei Jahre lang XML-Dokumente und LEI-Daten geprüft: Pflichtfelder, Formate, Konsistenz — Dokument für Dokument, von Hand. Die Prüfung war immer dieselbe, nur die Daten änderten sich.

Genau diese Wiederholung war der Anlass für dieses Projekt: Ich wollte wissen, wie man so eine Prüfung sauber automatisiert, statt sie zu wiederholen.

## Was das Tool macht

```
XML-Dateien  →  Parsing  →  Regelprüfung  →  Duplikat-Check  →  Report (CSV/JSON)
```

- **LEI-Validierung** nach ISO 17442, inklusive der mod-97-10-Prüfziffer (ISO 7064) — erkennt also nicht nur falsche Formate, sondern auch Tippfehler in formal korrekten Codes
- **Feldregeln:** Pflichtfelder, Datumsformat und Plausibilität (kein Datum in der Zukunft), ISO-3166-Ländercodes, erlaubte Statuswerte
- **Duplikaterkennung** über alle Dateien hinweg: jede Datei für sich korrekt, zusammen aber widersprüchlich
- **Report** als CSV oder JSON, mit Fehleranzahl und konkreter Fehlerbeschreibung pro Dokument
- **Exit-Codes** für Automatisierung: `0` = alles sauber, `1` = Fehler gefunden, `2` = Ausführungsfehler

## Verwendung

```bash
python src/validate_documents.py --input ./samples --report ./report.csv
python src/validate_documents.py --input ./samples --report ./report.json --format json
```

Beispielausgabe:

```
[INFO] entity_001.xml           OK
[INFO] entity_003_badchecksum.xml 1 Fehler
[INFO] entity_004_missing.xml   5 Fehler
[WARNING] Duplikat: LEI 529900T8BM49AURSDO55 in entity_001.xml, entity_005_duplicate.xml
[INFO] Ergebnis: 5 Dokumente geprüft, 4 fehlerhaft
```

Report (Auszug):

| file | lei | status | error_count | errors |
|---|---|---|---|---|
| entity_002.xml | 5493001KJTIIGC8Y1R12 | OK | 0 | |
| entity_003_badchecksum.xml | 529900T8BM49AURSDO99 | FEHLER | 1 | lei: LEI-Prüfziffer falsch (mod-97-10) |
| entity_004_missing.xml | | FEHLER | 5 | lei: LEI fehlt; legalName: Pflichtfeld ist leer; ... |

## Automatisierung mit Cron

Damit die Prüfung ohne manuelles Anstoßen läuft, wird das Skript zeitgesteuert ausgeführt:

```bash
# crontab -e
# Jeden Werktag um 6:30 Uhr alle eingegangenen Dokumente prüfen
30 6 * * 1-5 /usr/bin/python3 /opt/lei-validator/src/validate_documents.py \
    --input /data/incoming --report /data/reports/$(date +\%F).csv >> /var/log/lei-validator.log 2>&1
```

Der Exit-Code macht das Skript in Pipelines nutzbar: bei `1` kann ein Folgeschritt einen Alert auslösen, statt fehlerhafte Daten weiterzureichen.

## Wie die LEI-Prüfziffer funktioniert

Ein LEI hat 20 Zeichen; die letzten beiden sind Prüfziffern. Die Validierung nach ISO 7064 (mod-97-10):

1. Buchstaben in Zahlen umwandeln (A=10, B=11, … Z=35) — aus dem alphanumerischen Code wird eine lange Zahl
2. Diese Zahl modulo 97 rechnen
3. Das Ergebnis muss **1** sein, sonst ist der Code fehlerhaft

Dadurch fallen Tipp- und Zahlendreher auf, die eine reine Formatprüfung (Länge, erlaubte Zeichen) nicht bemerkt.

## Tests

```bash
python tests/test_validators.py       # 9 Tests, ohne externe Abhängigkeiten
python -m pytest tests/ -v            # alternativ mit pytest
```

## Projektstruktur

```
├── src/
│   ├── validators.py           # Validierungsregeln (je Regel eine testbare Funktion)
│   └── validate_documents.py   # CLI: Dateien einlesen, prüfen, Report schreiben
├── tests/
│   └── test_validators.py      # Unit-Tests der Regeln
├── samples/                    # Beispieldokumente (gültig + bewusst fehlerhaft)
└── README.md
```

## Technische Entscheidungen

- **Regeln als einzelne Funktionen:** Jede Regel gibt `None` (ok) oder eine Fehlermeldung zurück. Dadurch sind sie einzeln testbar und beliebig kombinierbar; neue Felder erfordern nur einen zusätzlichen Eintrag im Regelwerk.
- **Nur Standardbibliothek:** kein `pip install` nötig, das Skript läuft auf jedem System mit Python 3 — praktisch für Cron-Jobs auf Servern.
- **Fehler sammeln statt abbrechen:** Ein Dokument wird vollständig geprüft, damit der Report alle Probleme auf einmal zeigt, statt nach dem ersten Fehler zu stoppen.

## Stack

Python 3 (Standardbibliothek: `xml.etree.ElementTree`, `csv`, `json`, `re`, `argparse`, `logging`, `pathlib`), Cron

---

**Fourat Chaaben** · [GitHub](https://github.com/fourat-chaaben) · [LinkedIn](https://linkedin.com/in/fourat-chaaben)
