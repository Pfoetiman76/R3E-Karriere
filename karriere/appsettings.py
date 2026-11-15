"""App-Einstellungen fuer R3E Karriere (Qt-frei und damit unit-testbar).

Speichert den optionalen Fahrernamen (fuer Multiplayer-Sitzungen, in denen
die automatische Spielererkennung ueber das KI-Kennzeichen nicht greift)
und einen optionalen eigenen Pfad zur Ergebnis-Datenbank.
"""
import json
import os

SETTINGS_FILENAME = "settings.json"
DEFAULTS = {"driver_name": "", "results_db": "", "class_tiers": {}}


def _clean_class_tiers(value):
    if not isinstance(value, dict):
        return {}
    out = {}
    for k, v in value.items():
        try:
            out[str(k).strip()] = int(v)
        except (TypeError, ValueError):
            continue
    return out


def settings_path(app_dir):
    return os.path.join(app_dir, SETTINGS_FILENAME)


def load_settings(path):
    """Liest settings.json; fehlende Schluessel ergaenzt, korrupte Datei => Defaults."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = raw
        except (OSError, ValueError):
            data = {}
    s = dict(DEFAULTS)
    s.update({k: v for k, v in data.items() if k in DEFAULTS})
    s["driver_name"] = str(s["driver_name"] or "").strip()
    s["results_db"] = str(s["results_db"] or "").strip()
    s["class_tiers"] = _clean_class_tiers(s["class_tiers"])
    return s


def save_settings(path, settings):
    """Schreibt settings.json atomar (tmp + replace); Rueckgabe: gespeicherte Werte."""
    clean = {k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}
    clean["driver_name"] = str(clean["driver_name"] or "").strip()
    clean["results_db"] = str(clean["results_db"] or "").strip()
    clean["class_tiers"] = _clean_class_tiers(clean["class_tiers"])
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return clean
