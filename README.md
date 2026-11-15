# R3E Karriere

Karriere-Modus für RaceRoom: Wertet die Ergebnis-Datenbank von
[R3E Resultate](https://github.com/Pfoetiman76/R3E-Resultate) automatisch
aus und baut daraus eine durchgängige Karriere mit Meisterschaft, XP-Level
und Erfolgen.

## Konzept

- **Automatisch:** Alle Rennsitzungen (`Race`, `Race1`, `Race2`, ...), die
  R3E Resultate erfasst, zählen ohne weiteres Zutun in der Karriere. Die
  App liest die `results.db` von R3E Resultate **ausschließlich lesend**
  (gemäß R3E-Datenkonzept) und benötigt keinen eigenen Datenbestand.
- **Ohne eigene Persistenz:** Punkte, Level und Erfolge werden vollständig
  aus den Ergebnissen abgeleitet – auch das Freischaltdatum eines Erfolgs
  ist der Zeitstempel des Rennens, das ihn erstmals erfüllte. Damit ist die
  Karriere bei jedem Start konsistent zur Ergebnis-Historie.
- **Spielererkennung:** Bei Einzelspieler-Rennen wird der eigene Eintrag
  automatisch erkannt (einziger Fahrer ohne KI-Kennzeichen). Für
  Multiplayer-Sitzungen kann unter *Werkzeuge → Fahrernamen festlegen ...*
  der eigene Name hinterlegt werden.

## Meisterschaft

F1-Punkteschema: 25-18-15-12-10-8-6-4-2-1, plus ein Bonuspunkt für die
schnellste Rennrunde unter den Top 10. Die Punktetabelle umfasst das
komplette Fahrerfeld (inklusive KI-Gegner); der eigene Fahrer ist farbig
hervorgehoben.

## Entwicklung und Erfolge

- XP pro Rennen: Ziel 10, Podium +15, Sieg +25, Pole +10, schnellste
  Rennrunde +5, Ausfall 2. Ein Level alle 100 XP, mit Titel-Bändern
  (Rookie, Amateur, Semi-Profi, Profi, Meister, Legende).
- 22 Erfolge (Debüt, erster Sieg, Hattrick, Siegesserien, Streckenmeister,
  Fuhrpark u. a.), jeweils mit Fortschrittsanzeige und Freischalt-Datum.

## Voraussetzungen

- Installierte und genutzte App **R3E Resultate** (Standardpfad der
  Datenbank: `Dokumente\RaceRoom Results Companion\results.db`; abweichend
  wählbar über *Werkzeuge → Ergebnis-Datenbank wählen ...*).

## Bedienung

- Nach dem Start wird die Karriere sofort aufgebaut (F5 aktualisiert).
- Tab **Übersicht**: Level, XP-Balken, Kacheln (Rennen, Siege, Podien,
  Pole, Punkte ...) und die Rennhistorie.
- Tab **Meisterschaft**: Punktetabelle aller Fahrer.
- Tab **Erfolge**: alle Erfolge mit Fortschritt und Freischaltdatum.

## Entwicklung

```bash
python -m unittest discover -s tests   # 18 Unit-Tests
python main.py                         # App starten (PySide6)
```

## Release (CI)

Tag `v<APP_VERSION>` auf `main` pushen → GitHub Actions baut Tests,
PyInstaller-Ordner-Build und Inno-Setup-Installer
(`R3E-Karriere-Setup-<Version>.exe`) und hängt ihn ans Release.
