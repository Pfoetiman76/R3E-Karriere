"""Tests fuer den Karriere-Modus (karriere.careerstate)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from karriere import careerstate
from karriere.careerstate import (
    CareerModeError, accept_offer, active_championship, decline_offer,
    load_state, new_state, save_state, start_championship, tier_of,
    classes_of_tier, team_for_tier, test_reports, refresh,
    finish_championship, open_offers, filter_races_from, STATE_VERSION)


class FakeRace:
    """Minimaler RaceEvent-Ersatz (nur session_id/vehicle_class/points/
    position werden benoetigt)."""

    def __init__(self, session_id, vehicle_class, points=0, position=0):
        self.session_id = session_id
        self.vehicle_class = vehicle_class
        self.points = points
        self.position = position


def make_races(n, cls, start_sid=1, points=25, position=1):
    return [FakeRace(start_sid + i, cls, points=points, position=position)
            for i in range(n)]


class CareerStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "karriere.json")
        self.state = new_state()

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------- Persistenz --

    def test_state_roundtrip_and_corrupt_file(self):
        start_championship(self.state, "GT3-Saison", "GT3", 4)
        save_state(self.path, self.state)
        loaded = load_state(self.path)
        self.assertEqual(loaded["schema_version"], STATE_VERSION)
        self.assertEqual(loaded["championships"][0]["name"], "GT3-Saison")
        self.assertEqual(loaded["championships"][0]["tier"], 3)
        # Korrupte Datei => frischer Zustand
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{kein json")
        fresh = load_state(self.path)
        self.assertEqual(fresh["championships"], [])
        self.assertEqual(fresh["next_id"], 1)

    def test_missing_file_gives_new_state(self):
        s = load_state(self.path)
        self.assertEqual(s, new_state())

    # ------------------------------------------------ Klassen-Stufen --

    def test_tier_lookup_and_user_override(self):
        self.assertEqual(tier_of("GT3"), 3)
        self.assertEqual(tier_of("LMP1"), 6)
        self.assertEqual(tier_of("Unbekannte Klasse"), 3)   # Default
        self.assertEqual(tier_of("GT3", {"GT3": 5}), 5)     # Override
        self.assertEqual(classes_of_tier(6), ["FR3.5", "LMP1"])
        self.assertEqual(team_for_tier(3, 4), "Vulcan Racing")

    # ---------------------------------------------------- Meisterschaft --

    def test_only_one_active_championship(self):
        start_championship(self.state, "A", "GT3", 4)
        with self.assertRaises(CareerModeError):
            start_championship(self.state, "B", "GTE", 4)

    def test_empty_class_rejected(self):
        with self.assertRaises(CareerModeError):
            start_championship(self.state, "X", "", 4)

    def test_assign_only_matching_and_unused_races(self):
        champ = start_championship(self.state, "GT3-Saison", "GT3", 2)
        races = [FakeRace(1, "GT3"), FakeRace(2, "GTE"),
                 FakeRace(3, "GT3"), FakeRace(4, "GT3")]
        added = refresh(self.state, races)[0]
        self.assertEqual(added, 2)
        self.assertEqual(champ["session_ids"], [1, 3])
        self.assertEqual(champ["status"], "abgeschlossen")

    def test_no_assignment_without_active_championship(self):
        races = make_races(3, "GT3")
        added, finished = refresh(self.state, races)
        self.assertEqual(added, 0)
        self.assertIsNone(finished)

    # ------------------------------------------------------- Abschluss --

    def test_rating_and_offers_on_strong_season(self):
        """8 Siege: Bewertung 25/26 -> Aufstiegs- und Top-Angebote."""
        champ = start_championship(self.state, "GT3-Saison", "GT3", 2)
        races = make_races(2, "GT3", points=26)
        added, finished = refresh(self.state, races)
        self.assertIs(finished, champ)
        self.assertEqual(champ["points"], 52)
        self.assertEqual(champ["rating"], 1.0)
        types = sorted(o["type"] for o in champ["offers"])
        self.assertEqual(types, ["Aufstieg", "Verbleib", "Verbleib"])
        promo = [o for o in champ["offers"] if o["type"] == "Aufstieg"]
        self.assertIn(promo[0]["class"], classes_of_tier(4))   # Stufe 4
        self.assertEqual(promo[0]["team"], team_for_tier(4, 4))

    def test_offers_on_weak_season(self):
        """Punkteanteil unter 25 %: Abstiegs- und Rumpel-Angebot."""
        champ = start_championship(self.state, "GTE-Saison", "GTE", 2)
        races = make_races(2, "GTE", points=2, position=8)
        refresh(self.state, races)
        types = sorted(o["type"] for o in champ["offers"])
        self.assertEqual(types, ["Abstieg", "Verbleib"])
        self.assertEqual(
            [o for o in champ["offers"] if o["type"] == "Abstieg"][0]
            ["class"], "ADAC GT Masters")   # Stufe 3, alphabetisch erster

    def test_finish_uses_planned_race_count(self):
        champ = start_championship(self.state, "S", "GT3", 4)
        refresh(self.state, make_races(2, "GT3"))
        self.assertEqual(champ["status"], "aktiv")
        refresh(self.state, make_races(2, "GT3", start_sid=10))
        self.assertEqual(champ["status"], "abgeschlossen")
        self.assertEqual(len(champ["session_ids"]), 4)

    # ------------------------------------------------------ Testrennen --

    def test_test_reports_and_test_offer(self):
        champ = start_championship(self.state, "GT3-Saison", "GT3", 1)
        races = [FakeRace(1, "GT3", points=25, position=1),
                 FakeRace(2, "LMP2", points=25, position=1),
                 FakeRace(3, "LMP1", points=0, position=9)]
        refresh(self.state, races)
        # LMP2-Testrennen gewonnen -> zusaetzliches Testfahrer-Angebot
        types = [o["type"] for o in champ["offers"]]
        self.assertIn("Testfahrer", types)
        test_offer = [o for o in champ["offers"]
                      if o["type"] == "Testfahrer"][0]
        self.assertEqual(test_offer["class"], "LMP2")
        self.assertEqual(test_offer["team"], team_for_tier(5, 4))
        # LMP1 (Platz 9) bleibt ohne Angebot
        classes = [o["class"] for o in champ["offers"]]
        self.assertNotIn("LMP1", classes)
        # Testrennen-Statistik
        rep = test_reports(self.state, races)
        self.assertEqual(rep["LMP2"]["races"], 1)
        self.assertEqual(rep["LMP2"]["avg_position"], 1.0)

    def test_assigned_races_are_no_test_races(self):
        start_championship(self.state, "S", "GT3", 1)
        races = [FakeRace(1, "GT3", position=1)]
        refresh(self.state, races)
        self.assertEqual(test_reports(self.state, races), {})

    # ---------------------------------------------------------- Angebote --

    def test_accept_offer_sets_contract_and_declines_rest(self):
        champ = start_championship(self.state, "GT3-Saison", "GT3", 1)
        races = [FakeRace(1, "GT3", points=26, position=1)]
        refresh(self.state, races)
        offers = open_offers(self.state)
        self.assertEqual(len(offers), 3)
        accepted = accept_offer(self.state, offers[0]["id"])
        self.assertEqual(accepted["status"], "angenommen")
        self.assertEqual(self.state["current_class"], accepted["class"])
        self.assertEqual(self.state["current_team"], accepted["team"])
        self.assertEqual(open_offers(self.state), [])   # Rest abgelehnt

    def test_decline_offer(self):
        champ = start_championship(self.state, "S", "GT3", 1)
        refresh(self.state, [FakeRace(1, "GT3", points=13, position=4)])
        offers = open_offers(self.state)
        decline_offer(self.state, offers[0]["id"])
        self.assertEqual(open_offers(self.state),
                         offers[1:])
        with self.assertRaises(CareerModeError):
            decline_offer(self.state, 99999)

    # ------------------------------------------------- Startdatum-Filter --

    def test_filter_races_from(self):
        r_old = FakeRace(1, "GT3")
        r_old.timestamp = "2025-11-01 15:30:00"
        r_new = FakeRace(2, "GT3")
        r_new.timestamp = "2026-11-01 15:30:00"
        r_notime = FakeRace(3, "GT3")
        races = [r_old, r_new, r_notime]
        # Kein Datum: alles zaehlt
        self.assertEqual(filter_races_from(races, ""), races)
        self.assertEqual(filter_races_from(races, None), races)
        # Ab 2026: nur das neue Rennen (und Rennen ohne Zeitstempel)
        out = filter_races_from(races, "2026-01-01")
        self.assertEqual([r.session_id for r in out], [2, 3])
        # Ungueltige Eingaben deaktivieren den Filter nicht gefaehrlich
        self.assertEqual(filter_races_from(races, "kein-datum"), races)
        # Grenztag inklusive
        out = filter_races_from(races, "2025-11-01")
        self.assertIn(1, [r.session_id for r in out])

    def test_filter_blocks_assignment_before_start_date(self):
        start_championship(self.state, "S", "GT3", 2)
        r_old = FakeRace(1, "GT3", points=26, position=1)
        r_old.timestamp = "2020-01-01 10:00:00"
        r_new = FakeRace(2, "GT3", points=26, position=1)
        r_new.timestamp = "2026-01-02 10:00:00"
        added, finished = refresh(
            self.state, filter_races_from([r_old, r_new], "2026-01-01"))
        self.assertEqual(added, 1)
        self.assertIsNone(finished)   # nur 1 von 2 geplanten Rennen

    def test_second_championship_after_acceptance(self):
        champ = start_championship(self.state, "S1", "GT3", 1)
        refresh(self.state, [FakeRace(1, "GT3", points=26, position=1)])
        offers = open_offers(self.state)
        promo = [o for o in offers if o["type"] == "Aufstieg"][0]
        accepted = accept_offer(self.state, promo["id"])
        champ2 = start_championship(
            self.state, "S2", accepted["class"], 1)
        self.assertEqual(champ2["tier"], 4)
        self.assertEqual(self.state["championships"][-1]["id"], champ2["id"])


if __name__ == "__main__":
    unittest.main()
