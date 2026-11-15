"""Tests fuer App-Einstellungen (karriere.appsettings)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from karriere import appsettings


class AppSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "settings.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip(self):
        appsettings.save_settings(self.path,
                                  {"driver_name": "Marcel",
                                   "results_db": "C:\\x\\results.db"})
        s = appsettings.load_settings(self.path)
        self.assertEqual(s["driver_name"], "Marcel")
        self.assertEqual(s["results_db"], "C:\\x\\results.db")

    def test_defaults_on_missing_file(self):
        s = appsettings.load_settings(self.path)
        self.assertEqual(s, appsettings.DEFAULTS)

    def test_corrupt_file_falls_back(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{kein gueltiges json")
        s = appsettings.load_settings(self.path)
        self.assertEqual(s["driver_name"], "")

    def test_career_start_roundtrip_and_validation(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"career_start": "2026-11-01"}')
        s = appsettings.load_settings(self.path)
        self.assertEqual(s["career_start"], "2026-11-01")
        # Ungueltiges Datum wird geleert
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"career_start": "morgen"}')
        s = appsettings.load_settings(self.path)
        self.assertEqual(s["career_start"], "")

    def test_unknown_keys_ignored_and_strip(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"driver_name": "  Marcel  ", "other": 1}')
        s = appsettings.load_settings(self.path)
        self.assertEqual(s["driver_name"], "Marcel")
        self.assertNotIn("other", s)


if __name__ == "__main__":
    unittest.main()
