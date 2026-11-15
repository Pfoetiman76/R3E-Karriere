"""Update-Pruefung fuer R3E Karriere (Qt-frei, unit-testbar).

Fragt die GitHub-Releases-API nach dem neuesten Release ab und
vergleicht die Version mit APP_VERSION. Keine Abhaengigkeiten ueber
die Standardbibliothek (urllib).
"""
import json
import urllib.request

LATEST_URL = ("https://api.github.com/repos/Pfoetiman76/R3E-Karriere"
              "/releases/latest")
USER_AGENT = "R3E-Karriere-UpdateCheck"


def parse_version(tag):
    """'v0.3.1' -> (0, 3, 1); ungueltige Eingaben -> leeres Tupel."""
    t = str(tag or "").strip().lstrip("vV")
    parts = []
    for piece in t.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            break
    return tuple(parts)


def is_newer(remote_tag, local_version):
    """True, wenn remote_tag eine hoehere Version als local ist."""
    return parse_version(remote_tag) > parse_version(local_version)


def fetch_latest(timeout=4.0):
    """Liefert dict {tag, url, notes, exe_url} oder None bei Fehler.

    exe_url ist der Browser-Download-Link des Setup-Installers, falls
    das Release einen anhaengt.
    """
    req = urllib.request.Request(LATEST_URL, headers={
        "User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    exe_url = ""
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "").lower()
        if name.endswith(".exe") and "setup" in name:
            exe_url = asset.get("browser_download_url") or ""
            break
    return {
        "tag": str(data.get("tag_name") or ""),
        "url": str(data.get("html_url") or ""),
        "notes": str(data.get("body") or ""),
        "exe_url": exe_url,
    }
