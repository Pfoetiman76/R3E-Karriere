# R3E Karriere

Karriere-Modus für RaceRoom: Wertet die Ergebnis-Datenbank von
[R3E Resultate](https://github.com/Pfoetiman76/R3E-Resultate) automatisch
aus und baut daraus eine durchgängige Karriere mit Meisterschaften,
Vertragsangeboten, XP-Level und Erfolgen.

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

## Karriere-Modus

- **Meisterschaft anlegen:** Start in einer beliebigen Klasse (freie
  Wahl) mit einer selbst angelegten Meisterschaft: Name, Klasse und
  geplante Rennanzahl (Standard 8). Passende Rennen werden automatisch
  zugeordnet, solange die Meisterschaft läuft.
- **Angebote am Saisonende:** Ist die geplante Rennanzahl erreicht,
  entsteht je nach Ergebnis ein Angebotspaket – F1-Punkteschema als
  Bewertungsgrundlage (Anteil an den theoretisch möglichen Punkten):
  ab 45 % Aufstiegsangebot aus der nächsthöheren Klasse plus
  Topteam-Angebote, 25–45 % Spitzenteams der eigenen Klasse,
  unter 25 % Abstiegsangebot aus der nächsttieferen Klasse. Ein
  angenommenes Angebot setzt den neuen Kontrakt (Klasse + Team);
  die weiteren Angebote verfallen damit.
- **Testrennen:** Einzelrennen in anderen Klassen, die keiner
  Meisterschaft zugeordnet sind, zählen als Testrennen. Ein
  Durchschnittsplatz von 3 oder besser erzeugt ein zusätzliches
  Angebot dieser Klasse.
- **Karrieretafel (Vorbild Project CARS 2):** Der Karriere-Reiter zeigt
  den Rang (Level, Emblem, Titel, Erfolge) und die freigeschalteten
  Klassen-Stufen. Die erste Meisterschaft ist frei waehlbar; danach
  sind hoehere Stufen erst nach Aufstiegs-Angebot, Einladung oder
  starker Saison (Bewertung >= 45 %) verfuegbar.
- **Einladungs-Events:** Gute Testrennen (Durchschnittsplatz <= 3) in
  fremden Klassen erzeugen jederzeit eine Testfahrer-Einladung mit
  Kontrakt - analog den Einladungs-Events in Project CARS 2.
- **Automatisches Update:** Beim Start wird im Hintergrund das
  neueste GitHub-Release geprueft; bei einer neueren Version
  informiert die App und kann den Installer direkt herunterladen
  und starten (Werkzeuge → Nach Update suchen ...).
- **Karriere-Startdatum:** Unter *Werkzeuge →
  Karriere-Startdatum festlegen ...* laesst sich ein Datum (JJJJ-MM-TT)
  hinterlegen; ab dann zaehlen nur noch Rennen ab diesem Tag fuer
  Zuordnung zu Meisterschaften und Testrennen-Statistik (leer = alle
  Rennen).
- **Klassen-Hierarchie:** Vordefinierte R3E-Stufenleiter (Stufe 1 = DTC
  bis Stufe 6 = LMP1), frei editierbar unter *Werkzeuge →
  Klassen-Stufen bearbeiten ...*; unbekannte Klassen fallen auf
  Stufe 3 zurück.
- **Persistenz:** Der Karriere-Zustand (Kontrakt, Meisterschaften,
  Angebote) liegt in `karriere.json` im App-Ordner (Eigentum dieser
  App, atomar geschrieben); die `results.db` wird weiterhin nur
  lesend gelesen.
- **Geplant:** Einnahmen und Startgeld für höhere Klassen.

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
- Tab **Karriere**: Kontrakt, aktive Meisterschaft mit Fortschritt,
  offene Angebote (Annehmen/Ablehnen) und die Testrennen-Statistik.
- Tab **Übersicht (Dashboard)**: Level-Karte mit Rang-Emblem und
  Titel, KPI-Karten (Rennen, Siege, Podien, Pole, schnellste Runden,
  Erfolge), Verlaufs-Diagramm der kumulierten Punkte und XP
  (eigene QPainter-Chart, keine Zusatzabhängigkeit) und die
  Rennhistorie.
- Tab **Übersicht** (Kern): Level, XP-Balken, Kacheln (Rennen, Siege, Podien,
  Pole, Punkte ...) und die Rennhistorie.
- Tab **Meisterschaft**: Punktetabelle aller Fahrer, Platz 1-3 in
  Medaillenfarben (Gold/Silber/Bronze).
- Tab **Erfolge**: alle Erfolge mit Fortschritt und Freischaltdatum,
  freigeschaltete mit Stern-Emblem. Der Karriere-Reiter zeigt den
  Meisterschafts-Fortschritt als Balken, Kontrakt und Angebote mit
  Stufen- und Typ-Emblemen.

## Entwicklung

```bash
python -m unittest discover -s tests   # 45 Unit-Tests
python main.py                         # App starten (PySide6)
```

## Release (CI)

Tag `v<APP_VERSION>` auf `main` pushen → GitHub Actions baut Tests,
PyInstaller-Ordner-Build und Inno-Setup-Installer
(`R3E-Karriere-Setup-<Version>.exe`) und hängt ihn ans Release.
