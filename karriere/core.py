"""Karriere-Engine fuer R3E Karriere (Qt-frei, unit-testbar).

Wertet die Ergebnis-Datenbank von R3E Resultate (results.db) ausschliesslich
lesend aus und leitet daraus eine durchgaengige Karriere ab:

- Alle Rennsitzungen (session_type LIKE 'Race%') zaehlen automatisch.
- Der eigene Fahrer wird je Sitzung erkannt: entweder ueber den
  hinterlegten Fahrernamen (Multiplayer) oder - bei Einzelspieler-Sitzungen -
  als einziger Eintrag ohne KI-Kennzeichen (ai = 0).
- Meisterschaft: F1-Punkteschema (25-18-15-12-10-8-6-4-2-1) plus einen
  Bonuspunkt fuer die schnellste Rennrunde unter den Top 10. Die Tabelle
  umfasst das komplette Fahrerfeld (inklusive KI), der eigene Fahrer wird
  hervorgehoben.
- Persoenliche Entwicklung: XP pro Rennen (Ziel 10, Podium +15, Sieg +25,
  Pole +10, schnellste Runde +5, Ausfall 2) und Level daraus.
- Erfolge: ausschliesslich aus den Daten abgeleitet (keine eigene
  Persistenz noetig); das Freischaltdatum ist der Zeitstempel des
  Rennens, mit dem der Erfolg erstmals erfuellt war.

Schema von results.db (Eigentuemer: R3E Resultate, siehe r3e-datenkonzept):
sessions(id, digest, session_type, timestamp, track, layout, source_file)
entries(id, session_id, position, name, vehicle, team, laps, best_lap_ms,
        qual_ms, race_time_ms, finish_status, car_id, ai, vehicle_class,
        total_laps)
"""
import sqlite3

# F1-Punkteschema fuer Platz 1-10
POINTS = (25, 18, 15, 12, 10, 8, 6, 4, 2, 1)

# XP-Regeln je Rennen
XP_FINISH = 10       # Ziel
XP_PODIUM = 15       # zusaetzlich bei Platz 1-3
XP_WIN = 25          # zusaetzlich bei Sieg
XP_POLE = 10         # zusaetzlich bei Pole (schnellste Qualify-Zeit)
XP_FASTEST = 5       # zusaetzlich fuer schnellste Rennrunde
XP_DNF = 2           # Teilnahme bei Ausfall
XP_PER_LEVEL = 100   # Levelaufstieg je 100 XP

_LEVEL_TITLES = (
    (1, "Rookie"), (3, "Amateur"), (5, "Semi-Profi"), (7, "Profi"),
    (9, "Meister"), (11, "Legende"),
)


class CareerError(Exception):
    """Problem mit der Ergebnis-Datenbank (fehlt, leer oder falsches Schema)."""


def level_title(level: int) -> str:
    name = _LEVEL_TITLES[0][1]
    for threshold, title in _LEVEL_TITLES:
        if level >= threshold:
            name = title
    return name


class RaceEvent:
    """Ein gewertetes Rennen aus Sicht eines Treibers."""
    __slots__ = ("session_id", "timestamp", "track", "layout", "session_type",
                 "name", "vehicle", "vehicle_class", "position", "n_drivers",
                 "finished", "best_lap_ms", "pole", "fastest_lap", "points",
                 "xp", "laps")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k, 0) if k != "name" else kw.get(k, ""))

    @property
    def track_full(self) -> str:
        if self.layout and self.layout != "(Layout-Id)":
            return f"{self.track} - {self.layout}"
        return self.track

    @property
    def won(self) -> bool:
        return self.position == 1

    @property
    def podium(self) -> bool:
        return 1 <= self.position <= 3

    @property
    def hat_trick(self) -> bool:
        return self.pole and self.won and self.fastest_lap

    @property
    def double(self) -> bool:
        return self.pole and self.won


class Career:
    """Durchgaengige Karriere ueber alle Rennen der Ergebnis-Datenbank."""

    def __init__(self, db_path: str, driver_name: str = ""):
        self.db_path = db_path
        self.driver_name = (driver_name or "").strip()
        self._races = None

    # ------------------------------------------------------------- Zugang --

    def _connect(self):
        import os
        if not self.db_path or not os.path.isfile(self.db_path):
            raise CareerError(
                "Ergebnis-Datenbank nicht gefunden:\n%s\n\n"
                "Bitte den Pfad in Werkzeuge > Ergebnis-Datenbank waehlen ..."
                % (self.db_path or "(leer)"))
        try:
            # Schreibschutz: NUR lesender Zugriff gemaess Datenkonzept.
            conn = sqlite3.connect(
                "file:%s?mode=ro" % self.db_path.replace("?", "%3f"),
                uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:
            raise CareerError("Ergebnis-Datenbank nicht lesbar: %s" % exc)
        try:
            conn.execute(
                "SELECT id, session_type, timestamp, track, layout "
                "FROM sessions LIMIT 1")
            conn.execute(
                "SELECT id, session_id, position, name, vehicle, best_lap_ms,"
                " qual_ms, finish_status, ai, vehicle_class, laps "
                "FROM entries LIMIT 1")
        except sqlite3.Error:
            conn.close()
            raise CareerError(
                "Die Datei ist keine Ergebnis-Datenbank von R3E Resultate "
                "(Tabellen sessions/entries fehlen).")
        return conn

    # -------------------------------------------------------------- Fahrer --

    def _player_entry(self, entries):
        """Findet den eigenen Eintrag einer Sitzung.

        entries: Liste dicts (name, ai, ...). Prioritaet:
        1. exakter Namensmatch, falls driver_name gesetzt
        2. Einzelspieler: der einzige Eintrag mit ai = 0 (echter Fahrer)
        """
        if self.driver_name:
            for e in entries:
                if e["name"] == self.driver_name:
                    return e
            return None
        humans = [e for e in entries if e["ai"] == 0]
        if len(humans) == 1:
            return humans[0]
        return None

    # -------------------------------------------------------------- Rennen --

    def races(self):
        """Alle gewerteten Rennen (aeltestes zuerst); lazily gecached."""
        if self._races is not None:
            return self._races
        conn = self._connect()
        try:
            sess = conn.execute(
                "SELECT id, session_type, timestamp, track, layout "
                "FROM sessions WHERE session_type LIKE 'Race%' "
                "ORDER BY timestamp ASC, id ASC").fetchall()
            out = []
            for (sid, stype, ts, track, layout) in sess:
                entries = [dict(r) for r in conn.execute(
                    "SELECT id, position, name, vehicle, vehicle_class,"
                    " best_lap_ms, qual_ms, finish_status, ai, laps "
                    "FROM entries WHERE session_id = ?", (sid,)).fetchall()]
                if not entries:
                    continue
                me = self._player_entry(entries)
                if me is None:
                    continue   # Sitzung ohne erkennbaren eigenen Eintrag
                n_drivers = len([e for e in entries if e["position"] > 0]) \
                    or len(entries)
                bests = [e["best_lap_ms"] for e in entries
                         if e["best_lap_ms"] and e["best_lap_ms"] > 0]
                quals = [e["qual_ms"] for e in entries
                         if e["qual_ms"] and e["qual_ms"] > 0]
                fastest = min(bests) if bests else 0
                pole_ms = min(quals) if quals else 0
                pos = me["position"] or 0
                finished = (not me["finish_status"]
                            or me["finish_status"].lower() == "finished")
                points = POINTS[pos - 1] if 1 <= pos <= len(POINTS) else 0
                if points and me["best_lap_ms"] and fastest \
                        and me["best_lap_ms"] == fastest and pos <= 10:
                    points += 1   # Bonuspunkt schnellste Rennrunde
                xp = 0
                if finished:
                    xp += XP_FINISH
                    if pos <= 3:
                        xp += XP_PODIUM
                    if pos == 1:
                        xp += XP_WIN
                    if me["best_lap_ms"] and fastest \
                            and me["best_lap_ms"] == fastest:
                        xp += XP_FASTEST
                else:
                    xp += XP_DNF
                if me["qual_ms"] and pole_ms and me["qual_ms"] == pole_ms:
                    xp += XP_POLE
                out.append(RaceEvent(
                    session_id=sid, timestamp=ts or "", track=track or "",
                    layout=layout or "", session_type=stype or "",
                    name=me["name"], vehicle=me["vehicle"] or "",
                    vehicle_class=me["vehicle_class"] or "",
                    position=pos, n_drivers=n_drivers, finished=finished,
                    best_lap_ms=me["best_lap_ms"] or 0,
                    pole=bool(me["qual_ms"] and pole_ms
                             and me["qual_ms"] == pole_ms),
                    fastest_lap=bool(me["best_lap_ms"] and fastest
                                     and me["best_lap_ms"] == fastest),
                    points=points, xp=xp, laps=me["laps"] or 0))
            self._races = out
            return out
        finally:
            conn.close()

    def driver_name_detected(self) -> str:
        """Der erkannte eigene Fahrername (leer, wenn unbekannt)."""
        for r in self.races():
            return r.name
        return self.driver_name

    # -------------------------------------------------------- Meisterschaft --

    def standings(self):
        """Punktetabelle ueber das komplette Fahrerfeld, absteigend.

        Rueckgabe: Liste dicts mit name, points, wins, podium, races,
        is_player. Der eigene Fahrer ist markiert; bei gleicher Punktzahl
        entscheidet zuerst die Zahl der Siege, dann der Renneinsaetze.
        """
        return self._full_standings()

    def standings_for(self, session_ids):
        """Punktetabelle nur ueber die angegebenen Sitzungs-Ids."""
        conn = self._connect()
        try:
            return self._standings_sessions(list(session_ids), conn)
        finally:
            conn.close()

    def _full_standings(self):
        """Berechnet die Punktetabelle ueber ALLE Fahrer aller Rennen."""
        conn = self._connect()
        try:
            sessions = [r["session_id"] for r in conn.execute(
                "SELECT id AS session_id FROM sessions "
                "WHERE session_type LIKE 'Race%' "
                "ORDER BY timestamp ASC, id ASC").fetchall()]
            return self._standings_sessions(sessions, conn)
        finally:
            conn.close()

    def _standings_sessions(self, sessions, conn):
        """Punktetabelle ueber die Sitzungen einer Liste (Feld inkl. KI)."""
        pts = {}
        for sid in sessions:
            entries = [dict(r) for r in conn.execute(
                "SELECT position, name, ai, best_lap_ms "
                "FROM entries WHERE session_id = ?", (sid,)).fetchall()]
            if not entries:
                continue
            me = self._player_entry(entries)
            if me is None:
                continue   # fuer die Karriere nicht gezaehlte Sitzung
            bests = [e["best_lap_ms"] for e in entries
                     if e["best_lap_ms"] and e["best_lap_ms"] > 0]
            fastest = min(bests) if bests else 0
            for e in entries:
                if not e["name"] or not e["position"]:
                    continue
                p = POINTS[e["position"] - 1] \
                    if 1 <= e["position"] <= len(POINTS) else 0
                if p and fastest and e["best_lap_ms"] == fastest \
                        and e["position"] <= 10:
                    p += 1
                a = pts.setdefault(e["name"],
                                    {"name": e["name"], "points": 0,
                                     "wins": 0, "podium": 0, "races": 0,
                                     "is_player": False})
                a["points"] += p
                a["races"] += 1
                if e["position"] == 1:
                    a["wins"] += 1
                if 1 <= e["position"] <= 3:
                    a["podium"] += 1
        player = self.driver_name_detected()
        for a in pts.values():
            if player and a["name"] == player:
                a["is_player"] = True
        return sorted(pts.values(),
                      key=lambda a: (-a["points"], -a["wins"],
                                     -a["races"], a["name"]))

    # ---------------------------------------------------------------- XP --

    def xp_total(self) -> int:
        return sum(r.xp for r in self.races())

    def level(self) -> int:
        return self.xp_total() // XP_PER_LEVEL + 1

    def xp_into_level(self) -> int:
        return self.xp_total() % XP_PER_LEVEL

    # ------------------------------------------------------------- Statistik --

    def stats(self) -> dict:
        """Karriere-Gesamtzahlen des eigenen Fahrers."""
        races = self.races()
        wins = [r for r in races if r.won]
        return {
            "races": len(races),
            "wins": len(wins),
            "podiums": len([r for r in races if r.podium]),
            "finishes": len([r for r in races if r.finished]),
            "dnfs": len([r for r in races if not r.finished]),
            "poles": len([r for r in races if r.pole]),
            "fastest_laps": len([r for r in races if r.fastest_lap]),
            "points": sum(r.points for r in races),
            "xp": self.xp_total(),
            "level": self.level(),
            "tracks_won": len({r.track_full for r in wins}),
            "vehicles": len({r.vehicle for r in races if r.vehicle}),
            "classes": len({r.vehicle_class for r in races
                            if r.vehicle_class}),
            "tracks": len({r.track_full for r in races}),
        }

    # ------------------------------------------------------------- Erfolge --

    def achievements(self):
        """Alle Erfolge mit Fortschritt und Freischalt-Datum.

        Rueckgabe: Liste dicts mit id, title, desc, goal, current,
        unlocked (Zeitstempel-String oder '').
        """
        races = self.races()
        # Kumulative Zeitreihen fuer datumsbezogene Erfolge
        cum = []
        w = p = fl = poles = doubles = hattricks = 0
        win_streak = fin_streak = 0
        best_win_streak = best_fin_streak = 0
        tracks_won, vehicles, classes = set(), set(), set()
        for i, r in enumerate(races):
            w += 1 if r.won else 0
            p += 1 if r.podium else 0
            fl += 1 if r.fastest_lap else 0
            poles += 1 if r.pole else 0
            doubles += 1 if r.double else 0
            hattricks += 1 if r.hat_trick else 0
            win_streak = win_streak + 1 if r.won else 0
            fin_streak = fin_streak + 1 if r.finished else 0
            best_win_streak = max(best_win_streak, win_streak)
            best_fin_streak = max(best_fin_streak, fin_streak)
            if r.won:
                tracks_won.add(r.track_full)
            if r.vehicle:
                vehicles.add(r.vehicle)
            if r.vehicle_class:
                classes.add(r.vehicle_class)
            cum.append({"ts": r.timestamp, "wins": w, "podiums": p,
                        "fastest": fl, "poles": poles, "doubles": doubles,
                        "hattricks": hattricks, "races": i + 1,
                        "win_streak": win_streak, "fin_streak": fin_streak,
                        "tracks_won": len(tracks_won),
                        "vehicles": len(vehicles),
                        "classes": len(classes),
                        "xp": sum(x.xp for x in races[:i + 1]),
                        })

        def first_ts(predicate):
            for row in cum:
                if predicate(row):
                    return row["ts"]
            return ""

        # Restliche Gesamtzaehler
        s = self.stats()
        lv = self.level()
        defs = [
            ("erstrennen", "Debuet", "Das erste Karriere-Rennen beendet",
             1, s["races"], lambda row: row["races"] >= 1),
            ("rennfuchs", "Rennfuchs", "10 Rennen gefahren", 10,
             s["races"], lambda row: row["races"] >= 10),
            ("veteran", "Veteran", "50 Rennen gefahren", 50,
             s["races"], lambda row: row["races"] >= 50),
            ("hundert", "Hundertpaar", "100 Rennen gefahren", 100,
             s["races"], lambda row: row["races"] >= 100),
            ("erster_sieg", "Erster Sieg", "Ein Rennen gewonnen", 1,
             s["wins"], lambda row: row["wins"] >= 1),
            ("fuenf_siege", "Aufsteiger", "5 Rennen gewonnen", 5,
             s["wins"], lambda row: row["wins"] >= 5),
            ("zehn_siege", "Siegertyp", "10 Rennen gewonnen", 10,
             s["wins"], lambda row: row["wins"] >= 10),
            ("fuenfzig_siege", "Serien-Champion", "25 Rennen gewonnen", 25,
             s["wins"], lambda row: row["wins"] >= 25),
            ("erstes_podium", "Aufs Treppchen", "Ersten Podiumsplatz "
             "erreicht", 1, s["podiums"], lambda row: row["podiums"] >= 1),
            ("podium10", "Stammgast", "10 Podiumsplaetze erreicht", 10,
             s["podiums"], lambda row: row["podiums"] >= 10),
            ("erste_pole", "Aus der ersten Reihe", "Erste Pole-Position "
             "(schnellste Qualify-Zeit)", 1, s["poles"],
             lambda row: row["poles"] >= 1),
            ("schnellste_runde", "Tempospitze", "Schnellste Rennrunde "
             "gefahren", 1, s["fastest_laps"],
             lambda row: row["fastest"] >= 1),
            ("doppelschlag", "Doppelschlag", "Pole und Sieg im selben "
             "Rennen", 1, doubles, lambda row: row["doubles"] >= 1),
            ("hattrick", "Hattrick", "Pole, Sieg und schnellste Runde im "
             "selben Rennen", 1, hattricks,
             lambda row: row["hattricks"] >= 1),
            ("serie3", "Lauffeuer", "3 Siege in Folge", 3, best_win_streak,
             lambda row: row["win_streak"] >= 3),
            ("serie5", "Unaufhaltsam", "5 Siege in Folge", 5,
             best_win_streak, lambda row: row["win_streak"] >= 5),
            ("zielserie10", "Zuverlaessig", "10 Rennen in Folge "
             "ins Ziel gebracht", 10, best_fin_streak,
             lambda row: row["fin_streak"] >= 10),
            ("streckenmeister", "Streckenmeister", "Siege auf 5 "
             "verschiedenen Strecken", 5, s["tracks_won"],
             lambda row: row["tracks_won"] >= 5),
            ("klassensammler", "Allrounder", "In 5 verschiedenen "
             "Fahrzeugklassen gefahren", 5, s["classes"],
             lambda row: row["classes"] >= 5),
            ("fuhrpark", "Fuhrpark", "10 verschiedene Fahrzeuge "
             "gefahren", 10, s["vehicles"],
             lambda row: row["vehicles"] >= 10),
            ("level5", "Gelernt", "Level 5 erreicht", 5, lv,
             lambda row: row["xp"] // XP_PER_LEVEL + 1 >= 5),
            ("level10", "Meisterklasse", "Level 10 erreicht", 10, lv,
             lambda row: row["xp"] // XP_PER_LEVEL + 1 >= 10),
        ]
        out = []
        for (aid, title, desc, goal, current, pred) in defs:
            unlocked = first_ts(pred) if pred else ""
            if unlocked is None:
                unlocked = ""
            out.append({"id": aid, "title": title, "desc": desc,
                        "goal": goal, "current": min(current, goal),
                        "unlocked": unlocked})
        return out
