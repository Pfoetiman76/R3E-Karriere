"""Standardpfade fuer R3E Karriere (Windows zuerst, portabler Fallback).

Wichtig gemaess R3E-Datenkonzept: Diese App liest die Ergebnis-Datenbank
von R3E Resultate NUR lesend und schreibt ausschliesslich in ihren
eigenen App-Ordner (settings.json).
"""
import os

APP_DIR_NAME = "R3E Karriere"
RESULTS_APP_DIR_NAME = "RaceRoom Results Companion"


def _windows_documents():
    """Liefert den Windows-Dokumente-Ordner oder None."""
    try:
        import ctypes
        import ctypes.wintypes
        from ctypes import windll
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5
        if windll.shfolder.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return buf.value
    except Exception:
        pass
    return None


def default_app_dir():
    base = os.path.join(_windows_documents() or os.path.expanduser("~"),
                        APP_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    return base


def default_results_db():
    """Standardpfad der Ergebnis-Datenbank von R3E Resultate."""
    docs = _windows_documents() or os.path.expanduser("~")
    return os.path.join(docs, RESULTS_APP_DIR_NAME, "results.db")


def career_state_path(app_dir):
    """Pfad der Karriere-Datei (karriere.json, Eigentum dieser App)."""
    return os.path.join(app_dir, "karriere.json")
