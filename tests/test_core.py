"""Tests fuer die Karriere-Engine (karriere.core)."""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from karriere.core import Career, CareerError, POINTS, XP_PER_LEVEL, \
    level_title

_SCHEMA = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest TEXT UNIQUE NOT NULL,
    session_type TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    track TEXT DEFAULT '',
    layout TEXT DEFAULT '',
    source_file TEXT DEFAULT ''
);
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    vehicle TEXT DEFAULT '',
    team TEXT DEFAULT '',
    laps INTEGER DEFAULT 0,
    best_lap_ms INTEGER DEFAULT 0,
    qual_ms INTEGER DEFAULT 0,
    race_time_ms INTEGER DEFAULT 0,
    finish_status TEXT DEFAULT '',
    car_id INTEGER DEFAULT 0,
    ai INTEGER DEFAULT -1,
    vehicle_class TEXT DEFAULT '',
    total_laps INTEGER DEFAULT -1
);
"""


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def add_session(conn, sid, stype="Race", ts="2026-11-01 12:00:00",
                track="Hockenheim", layout="GP", entries=()):
    """entries: (name, position, best_lap_ms, qual_ms, ai, finish_status,
    vehicle, vehicle_class)"""
    conn.execute(
        "INSERT INTO sessions (id, digest, session_type, timestamp, track,"
        " layout, source_file) VALUES (?,?,?,?,?,?,?)",
        (sid, "d%d" % sid, stype, ts, track, layout, "f%d.txt" % sid))
    for i, e in enumerate(entries):
        name, pos, best, qual, ai, status, veh, vclass = (
            e + (None,) * 8)[:8]
        conn.execute(
            "INSERT INTO entries (session_id, position, name, vehicle,"
            " best_lap_ms, qual_ms, finish_status, ai, vehicle_class)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, pos or 0, name, veh or "", best or 0, qual or 0,
             status or "", -1 if ai is None else ai, vclass or ""))
    conn.commit()


def sp_field(name="Marcel", pos=1, best=90000, qual=60000, veh="GT3-A",
             vclass="GT3"):
    """Eigener Fahrer im Einzelspieler (ai=0)."""
    return (name, pos, best, qual, 0, "Finished", veh, vclass)


def ai(name, pos, best=100000, qual=70000):
    return (name, pos, best, qual, 1, "Finished", "", "")


class CareerEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "results.db")
        self.conn = make_db(self.db)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def career(self, driver=""):
        return Career(self.db, driver)

    # ------------------------------------------------- Spielererkennung --

    def test_player_autodetected_in_sp(self):
        add_session(self.conn, 1, entries=[
            sp_field(pos=3), ai("Alex Bachoura", 1), ai("Bob_ai", 2)])
        c = self.career()
        self.assertEqual(len(c.races()), 1)
        self.assertEqual(c.races()[0].name, "Marcel")
        self.assertEqual(c.races()[0].position, 3)

    def test_driver_name_overrides(self):
        add_session(self.conn, 1, entries=[
            ("Marcel", 1, 90000, 60000, 1, "", "", ""),   # KI-Marcel
            ("Fritz", 2, 95000, 65000, 0, "", "", "")])
        c = self.career(driver="Marcel")
        self.assertEqual(c.races()[0].name, "Marcel")
        self.assertEqual(c.races()[0].position, 1)

    def test_race_without_player_is_skipped(self):
        add_session(self.conn, 1, entries=[ai("Alex Bachoura", 1)])
        add_session(self.conn, 2, entries=[sp_field(pos=1)])
        c = self.career()
        self.assertEqual(len(c.races()), 1)
        self.assertEqual(c.races()[0].session_id, 2)

    def test_practice_sessions_ignored(self):
        add_session(self.conn, 1, stype="Practice",
                    entries=[sp_field(pos=1)])
        add_session(self.conn, 2, stype="Qualify", entries=[sp_field()])
        add_session(self.conn, 3, stype="Race2", entries=[sp_field()])
        c = self.career()
        self.assertEqual([r.session_type for r in c.races()], ["Race2"])

    # ----------------------------------------------------------- Punkte --

    def test_points_scheme_and_bonus(self):
        entries = [sp_field(pos=1, best=80000), ai("A", 2, best=81000),
                   ai("B", 3), ai("C", 4), ai("D", 5), ai("E", 6),
                   ai("F", 7), ai("G", 8), ai("H", 9), ai("I", 10),
                   ai("J", 11)]
        add_session(self.conn, 1, entries=entries)
        c = self.career()
        r = c.races()[0]
        self.assertEqual(r.points, POINTS[0] + 1)   # Sieg + Bonuspunkt
        st = {a["name"]: a["points"] for a in c.standings()}
        self.assertEqual(st["Marcel"], POINTS[0] + 1)
        self.assertEqual(st["A"], POINTS[1])
        self.assertEqual(st["J"], 0)   # Platz 11: keine Punkte

    def test_dnf_gets_no_points_but_xp(self):
        add_session(self.conn, 1, entries=[
            sp_field(pos=1, best=0, qual=0), ai("A", 1)])
        # Eigener Fahrer: DNF (Position 0, Ausfall-Status)
        self.conn.execute("UPDATE entries SET position = 0, "
                          "finish_status = 'DNF' WHERE session_id = 1 "
                          "AND ai = 0")
        self.conn.commit()
        c = self.career()
        r = c.races()[0]
        self.assertEqual(r.points, 0)
        self.assertEqual(r.xp, 2)   # Teilnahme-XP

    # ------------------------------------------------------------- XP/Level --

    def test_xp_and_level(self):
        add_session(self.conn, 1, entries=[
            sp_field(pos=1, best=80000, qual=55000), ai("A", 2, best=90000)])
        c = self.career()
        r = c.races()[0]
        # Ziel + Podium + Sieg + schnellste Runde + Pole
        self.assertEqual(r.xp, 10 + 15 + 25 + 5 + 10)
        self.assertEqual(c.xp_total(), 65)
        self.assertEqual(c.level(), 1)
        self.assertEqual(level_title(1), "Rookie")
        self.assertEqual(level_title(7), "Profi")

    # --------------------------------------------------------- Meisterschaft --

    def test_standings_order_and_player_flag(self):
        add_session(self.conn, 1, entries=[
            sp_field(pos=2), ai("A", 1)])
        add_session(self.conn, 2, ts="2026-11-02 12:00:00", entries=[
            sp_field(pos=2), ai("A", 3)])
        c = self.career()
        st = c.standings()
        # A: 25 (Sieg) + 15 (Platz 3) = 40 Punkte vor Marcel
        # (18 + Bonuspunkt schnellste Runde, je Rennen)
        self.assertEqual(st[0]["name"], "A")
        self.assertEqual(st[0]["points"], 40)
        self.assertEqual(st[1]["name"], "Marcel")
        self.assertTrue(st[1]["is_player"])
        self.assertEqual(st[1]["points"], (POINTS[1] + 1) * 2)

    # ------------------------------------------------------------ Erfolge --

    def test_achievements_unlock_dates(self):
        add_session(self.conn, 1, ts="2026-11-01 12:00:00", entries=[
            sp_field(pos=1)])
        add_session(self.conn, 2, ts="2026-11-02 12:00:00", entries=[
            sp_field(pos=1)])
        add_session(self.conn, 3, ts="2026-11-03 12:00:00", entries=[
            sp_field(pos=1)])
        c = self.career()
        by_id = {a["id"]: a for a in c.achievements()}
        self.assertEqual(by_id["erstrennen"]["unlocked"],
                         "2026-11-01 12:00:00")
        self.assertEqual(by_id["erster_sieg"]["unlocked"],
                         "2026-11-01 12:00:00")
        self.assertEqual(by_id["serie3"]["unlocked"],
                         "2026-11-03 12:00:00")
        self.assertEqual(by_id["serie5"]["unlocked"], "")
        self.assertEqual(by_id["fuenf_siege"]["current"], 3)

    def test_achievement_progress_capped(self):
        add_session(self.conn, 1, entries=[sp_field(pos=1)])
        c = self.career()
        by_id = {a["id"]: a for a in c.achievements()}
        self.assertEqual(by_id["erster_sieg"]["current"], 1)
        self.assertEqual(by_id["erster_sieg"]["goal"], 1)

    def test_stats_and_streaks(self):
        entries1 = [sp_field(pos=1, best=80000, qual=55000),
                    ai("A", 2, best=90000)]
        add_session(self.conn, 1, ts="2026-11-01 12:00:00",
                    entries=entries1)
        add_session(self.conn, 2, ts="2026-11-02 12:00:00", track="Spa",
                    entries=[sp_field(pos=4)])
        c = self.career()
        s = c.stats()
        self.assertEqual(s["races"], 2)
        self.assertEqual(s["wins"], 1)
        self.assertEqual(s["finishes"], 2)
        # Beide Rennen: schnellste Qualify-Zeit des Spielers (60000 < 70000)
        self.assertEqual(s["poles"], 2)
        # Beide Rennen: Spielers Bestzeit (90000) vor KI (100000)
        self.assertEqual(s["fastest_laps"], 2)
        self.assertEqual(s["tracks"], 2)

    # ----------------------------------------------------------- Fehler --

    def test_missing_db_raises(self):
        c = Career(os.path.join(self.tmp.name, "gibtsnicht.db"))
        with self.assertRaises(CareerError):
            c.races()

    def test_wrong_schema_raises(self):
        path = os.path.join(self.tmp.name, "leer.db")
        sqlite3.connect(path).close()
        c = Career(path)
        with self.assertRaises(CareerError):
            c.races()

    def test_progression_cumulative(self):
        add_session(self.conn, 1, entries=[
            sp_field(pos=1), ai("Alex Bachoura", 2)])
        add_session(self.conn, 2, entries=[
            sp_field(pos=2), ai("Alex Bachoura", 1)])
        c = self.career()
        prog = c.progression()
        self.assertEqual(len(prog), c.stats()["races"])
        self.assertEqual([row["races"] for row in prog],
                         list(range(1, len(prog) + 1)))
        # Punkte und XP steigen kumulativ und enden mit den Summen
        self.assertEqual(prog[-1]["points"], c.stats()["points"])
        self.assertEqual(prog[-1]["xp"], c.stats()["xp"])
        for a, b in zip(prog, prog[1:]):
            self.assertGreaterEqual(b["points"], a["points"])
            self.assertGreaterEqual(b["xp"], a["xp"])

    def test_version(self):
        from karriere.models import APP_VERSION
        self.assertEqual(APP_VERSION, "0.6.0")


if __name__ == "__main__":
    unittest.main()
