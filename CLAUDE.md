# CLAUDE.md — R3E Karriere

Kontextdatei fuer Claude Code. Bitte beim Arbeiten an diesem Repository
die Konventionen unten beachten.

## Projekt

R3E Karriere ist eine eigenstaendige PySide6-Desktop-App (Windows), die aus
der Ergebnis-Datenbank von R3E-Resultate (`results.db`) automatisch eine
durchgaengige RaceRoom-Karriere ableitet: Meisterschaften mit F1-Punktetabelle,
Vertragsangebote nach Saisonende, Testrennen/Einladungen, XP-Level (Rookie bis
Legende) und 22 Erfolge. Optik im Stil der Project CARS 2 Karriere-Hubs,
Akzentfarbe RaceRoom-Rot #e8212b, tiefschwarzer Hintergrund.

Repo: https://github.com/Pfoetiman76/R3E-Karriere (Owner Pfoetiman76,
Branch main, Bearbeitung durch Marcel Wijnandts).

## Datenkonzept (verbindlich)

- `results.db` gehoert R3E-Resultate und wird AUSSCHLIESSLICH lesend
  geoeffnet (`sqlite3 ... mode=ro`). Niemals dort schreiben.
- Eigene Dateien im App-Ordner `Dokumente\R3E Karriere`:
  `settings.json` (driver_name, results_db, class_tiers, career_start)
  und `karriere.json` (Karriere-Zustand, schema_version 1, atomar via
  tmp + os.replace).
- Punkte/XP/Erfolge sind stateless: sie werden bei jedem Start aus der
  Rennhistorie neu abgeleitet (Freischaltdatum eines Erfolgs =
  Zeitstempel des Rennens, das ihn erstmals erfuellte).

## Struktur

- `karriere/models.py` — Konstanten inkl. APP_VERSION und APP_NAME.
- `karriere/paths.py`, `karriere/appsettings.py` — Pfade/Einstellungen.
- `karriere/core.py` — Karriere-Engine (Qt-frei, unit-testbar):
  Spielererkennung (driver_name oder ai=0), Punkte, XP, progression().
- `karriere/careerstate.py` — Karriere-Modus (Qt-frei): Meisterschaften,
  Angebote (>=45 % Aufstieg, 25-45 % Mittelfeld, <25 % Abstieg),
  Einladungen, unlocked_tiers, reset_state().
- `karriere/widgets.py` — Qt-Widgets: KpiCard, TrendChart (QPainter, keine
  externen Chart-Libs), HubHeader, HubCard, TierLadder, section_label.
- `karriere/theme.py` — QSS (PCARS2-Hub-Stil), dark_qss()/apply_dark_theme().
- `karriere/updatecheck.py` — GitHub releases/latest Abgleich (urllib).
- `main.py` — GUI: Tabs Karriere/Uebersicht/Meisterschaft/Erfolge,
  Werkzeuge-Menue, Update-Check (QTimer beim Start).
- `tests/` — 45 Unit-Tests (core, career, settings, ui_names).
- `tools/gen_icon.py` — reiner-Python-Icon-Generator (nur zlib/struct).
- `installer/r3e_karriere.spec` — PyInstaller-Ordner-Build.
- `installer/setup.iss` — Inno Setup (Version aus APP_VERSION-Env).
- `.github/workflows/release.yml` — Tag v* -> Tests -> Icon-Generierung ->
  PyInstaller -> Inno -> Release-Asset R3E-Karriere-Setup-<ver>.exe.

## Konventionen (bitte strikt einhalten)

1. Version: steht in `karriere/models.py` APP_VERSION; der Test
   `tests/test_core.py::test_version` muss synchron angepasst werden.
   Features = minor-Bump (0.7.0), Fixes = patch-Bump.
2. Release: Tag exakt `v` + APP_VERSION auf main. Marcel legt das Release
   auf GitHub an; die CI baut den Installer.
3. Code in .py-Dateien ASCII-transliteriert schreiben (ae/oe/ue statt
   Umlaute; so ist der gesamte Bestand gehalten). README.md darf Umlaute.
4. Kern-Logik Qt-frei halten und in `karriere/` legen; nur GUI in
   `main.py`/`widgets.py`.
5. Jede Aenderung: `python -m unittest discover -s tests` muss gruen
   bleiben. Die Regressionstests in `tests/test_ui_names.py` pruefen
   statisch per AST:
   a) alle in main.py benutzten Q*-Namen muessen importiert sein,
   b) auf Modulebene benutzte Namen muessen vorher definiert sein
      (gilt fuer main.py + karriere/*.py).
6. PyInstaller 6: PYZ(a.pure) ohne cipher-Argument.
7. Binary-Dateien werden NICHT committet: assets/icon.ico erzeugt die CI
   vor dem Build per `python tools/gen_icon.py` (Pruefung `test -f`).
   PyInstaller: icon=../assets/icon.ico + datas=[("../assets/icon.ico",
   "assets")]; Inno: SetupIconFile={#SourcePath}\..\assets\icon.ico.
8. Antworten/Commits auf Deutsch; freundlich, praezise, ohne Emojis.

## Bekannte Stolpersteine (aus der Fehlerhistorie)

- Fehlende Qt-Importe crashen NUR die paketierte App (NameError zur
  Laufzeit); py_compile und die Qt-freien Unit-Tests deckten das nicht ab
  -> deshalb Regel 5a/5b.
- Vorwaertsverweise auf Modulebene (Name vor Definition benutzt) crashen
  erst beim Import der paketierten App -> Regel 5b.
- PySide6 ist in der Linux-Test-Umgebung nicht installierbar; GUI-Aenderungen
  sind nur statisch pruefbar. Vor einem Release bitte einmal lokal
  `python main.py` ausfuehren.
- Update-Dialog: btn_dl nur bei gefuelltem exe_url anbieten.

## Entwicklung lokal

```bash
python -m unittest discover -s tests   # 45 Unit-Tests
python main.py                         # App starten (benoetigt PySide6)
python tools/gen_icon.py               # assets/icon.ico erzeugen
```

## Betrieb

Damit die App Daten zeigt, muessen RaceRoom gelaufen sein und
R3E-Resultate die Sitzungen in results.db importiert haben. Waehrend der
Nutzung muss keine andere App laufen.
