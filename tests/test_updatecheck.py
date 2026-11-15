"""Tests fuer die Update-Pruefung (karriere.updatecheck)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from karriere import updatecheck


class UpdateCheckTest(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(updatecheck.parse_version("v0.4.0"), (0, 4, 0))
        self.assertEqual(updatecheck.parse_version("0.10.2"), (0, 10, 2))
        self.assertEqual(updatecheck.parse_version(""), ())
        self.assertEqual(updatecheck.parse_version("abc"), ())
        self.assertEqual(updatecheck.parse_version(None), ())

    def test_is_newer(self):
        self.assertTrue(updatecheck.is_newer("v0.5.0", "0.4.0"))
        self.assertTrue(updatecheck.is_newer("v0.4.1", "v0.4.0"))
        self.assertFalse(updatecheck.is_newer("v0.4.0", "0.4.0"))
        self.assertFalse(updatecheck.is_newer("v0.3.9", "0.4.0"))
        self.assertFalse(updatecheck.is_newer("kein-tag", "0.4.0"))
        # Laengere Versionen schlagen kuerzere (0.4.0.1 > 0.4.0)
        self.assertTrue(updatecheck.is_newer("v0.4.0.1", "0.4.0"))

    def test_fetch_latest_offline_returns_none(self):
        """Ohne Netzwerk/Server liefert fetch_latest kapselt None."""
        url_bak = updatecheck.LATEST_URL
        try:
            updatecheck.LATEST_URL = "http://127.0.0.1:1/kein-server"
            self.assertIsNone(updatecheck.fetch_latest(timeout=1.0))
        finally:
            updatecheck.LATEST_URL = url_bak


if __name__ == "__main__":
    unittest.main()
