"""Karriere-Modus-Logik fuer R3E Karriere (Qt-frei, unit-testbar).

Aufbau gemaess Marcels Vorgabe:
- Start in einer beliebigen Klasse mit einer Meisterschaft.
- Eine Meisterschaft endet nach der festgelegten Rennanzahl; danach
  entstehen je nach Ergebnis Angebote von staerkeren oder schwaecheren
  Klassen sowie von anderen Teams derselben Klasse.
- Einzelrennen in anderen Klassen zaehlen als Testrennen und
  beeinflussen die Angebote.
- Einnahmen und Startgeld sind bewusst noch nicht enthalten (geplant
  fuer eine spaetere Version).

Persistenz: karriere.json im eigenen App-Ordner (Eigentum dieser App,
schema_version 1, atomar geschrieben). Die results.db von R3E Resultate
wird weiterhin nur lesend gelesen.
"""
import json
import os

STATE_FILENAME = "karriere.json"
STATE_VERSION = 1
DEFAULT_PLANNED_RACES = 8
MAX_POSSIBLE_POINTS = 26   # Sieg (25) + Bonuspunkt schnellste Runde

# Schwellenwerte der Angebotsbewertung (Punkteanteil am Moeglichen)
PROMOTION_RATIO = 0.45     # ab hier: Angebot aus einer hoeheren Klasse
RELEGATION_RATIO = 0.25    # darunter: Angebot aus einer tieferen Klasse
TEST_AVG_POS = 3.0         # Testrennen: max. Durchschnittsposition

DEFAULT_TIER = 3           # Stufe fuer unbekannte Klassen
MAX_TIER = 6               # hoechste Klassen-Stufe

# Vordefinierte R3E-Klassen-Hierarchie (Stufe 1 = langsamste).
# In den Einstellungen frei editierbar (class_tiers), unbekannte Klassen
# fallen auf DEFAULT_TIER zurueck.
DEFAULT_CLASS_TIERS = {
    "DTC": 1, "STCC": 1,
    "DTM 1992": 2, "Gruppe 5": 2,
    "ADAC GT Masters": 3, "GT3": 3, "GTR3": 3,
    "GTE": 4, "GTO": 4, "GT1": 4,
    "LMP3": 5, "LMP2": 5,
    "LMP1": 6, "FR3.5": 6,
}

# Fiktive Teams je Stufe: (Name, Staerke 1 = unteres Mittelfeld .. 4 = Top)
_TEAM_POOL = {
    1: [("Nordloop Racing", 1), ("Westwind Motorsport", 2),
        ("Adler Rennsport", 3), ("Blitz GP", 4)],
    2: [("Rheintal Motorsport", 1), ("Falcon Racing", 2),
        ("Isartal Rennsport", 3), ("Phantom Works", 4)],
    3: [("Eifel Racing", 1), ("Suedkurve Motorsport", 2),
        ("Kaiser Rennsport", 3), ("Vulcan Racing", 4)],
    4: [("Grenzland Racing", 1), ("Stahlross Team", 2),
        ("Loewengang Motorsport", 3), ("Aurora Racing", 4)],
    5: [("Nordsee Racing", 1), ("Taunus Motorsport", 2),
        ("Silberpfeil Team", 3), ("Pegasos Racing", 4)],
    6: [("Finkenherd Racing", 1), ("Rheingold Motorsport", 2),
        ("Kaiserpreis Rennsport", 3), ("Titan Grand Prix", 4)],
}


class CareerModeError(Exception):
    """Fehler bei der Karriere-Verwaltung."""


# ------------------------------------------------------------ Klassen --

def merged_tiers(tiers=None):
    """Default-Hierarchie + benutzerdefinierte Zuordnungen."""
    m = dict(DEFAULT_CLASS_TIERS)
    if isinstance(tiers, dict):
        for k, v in tiers.items():
            if k:
                try:
                    m[str(k).strip()] = int(v)
                except (TypeError, ValueError):
                    continue
    return m


def tier_of(vehicle_class, tiers=None):
    return merged_tiers(tiers).get(
        (vehicle_class or "").strip(), DEFAULT_TIER)


def classes_of_tier(tier, tiers=None):
    m = merged_tiers(tiers)
    return sorted(c for c, t in m.items() if t == tier)


def team_for_tier(tier, strength):
    pool = _TEAM_POOL.get(min(max(int(tier), 1), 6))
    for name, s in pool:
        if s == strength:
            return name
    return pool[-1][0]


def strength_label(strength):
    return {1: "Unteres Mittelfeld", 2: "Mittelfeld",
            3: "Spitzenteam", 4: "Topteam"}.get(int(strength), "Team")


def filter_races_from(races, start_date):
    """Laesst nur Rennen ab einem Datum (YYYY-MM-DD) zaehlen.

    Ein leeres oder ungueltiges Datum deaktiviert den Filter (alles
    zaehlt). Zeitstempel werden lexikographisch verglichen, daher
    funktionieren ISO-aehnliche Formate ('YYYY-MM-DD ...').
    Rennen ohne Zeitstempel werden zur Sicherheit behalten.
    """
    start = (start_date or "").strip()
    if not start:
        return list(races)
    try:
        year, month, day = (int(x) for x in start.split("-"))
        assert 1 <= month <= 12 and 1 <= day <= 31
    except (ValueError, AssertionError):
        return list(races)   # ungueltiges Datum => Filter aus
    out = []
    for r in races:
        ts = getattr(r, "timestamp", "") or ""
        if not ts or ts >= start:
            out.append(r)
    return out


# -------------------------------------------------------------- Zustand --

def new_state():
    return {
        "schema_version": STATE_VERSION,
        "current_class": "",
        "current_team": "",
        "championships": [],
        "next_id": 1,
    }


def load_state(path):
    """Liest karriere.json; korrupte Datei => frischer Zustand."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = raw
        except (OSError, ValueError):
            data = {}
    s = new_state()
    s["current_class"] = str(data.get("current_class") or "")
    s["current_team"] = str(data.get("current_team") or "")
    if isinstance(data.get("championships"), list):
        s["championships"] = [c for c in data["championships"]
                              if isinstance(c, dict)]
    if isinstance(data.get("invitations"), list):
        s["invitations"] = [i for i in data["invitations"]
                            if isinstance(i, dict)]
    try:
        s["next_id"] = max(1, int(data.get("next_id", 1)))
    except (TypeError, ValueError):
        s["next_id"] = len(s["championships"]) + 1
    return s


def save_state(path, state):
    """Schreibt karriere.json atomar (tmp + replace)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------- Stufen-Freischaltung --

def unlocked_tiers(state, tiers=None):
    """Freigeschaltete Klassen-Stufen (Karrieretafel).

    - Stufe 1 ist immer freigeschaltet (Start in beliebiger Klasse
      gemaess Vorgabe: nur die Folge-Meisterschaften sind gebunden).
    - Freigeschaltet sind zudem: Stufe der aktuellen Klasse, die
      Stufen jeder beendeten Meisterschaft (bei Bewertung >= 45 %
      zusaetzlich die naechsthoehere Stufe), Stufen angenommener
      Angebote sowie angenommener Einladungen.
    """
    m = merged_tiers(tiers)

    def t(cls):
        return m.get((cls or "").strip(), DEFAULT_TIER)

    out = {1}
    if state.get("current_class"):
        out.add(t(state["current_class"]))
    for c in state.get("championships") or []:
        ct = c.get("tier") or t(c.get("vehicle_class"))
        out.add(ct)
        if (c.get("rating") or 0) >= PROMOTION_RATIO:
            out.add(min(ct + 1, MAX_TIER))
    for c in state.get("championships") or []:
        for o in c.get("offers") or []:
            if o.get("status") == "angenommen":
                out.add(t(o.get("class")))
    for inv in state.get("invitations") or []:
        out.add(t(inv.get("class")))
    return out


def tier_ranges(tiers):
    """Menge von Stufen als Text, z. B. '1-3, 5'."""
    nums = sorted(set(int(t) for t in tiers))
    parts = []
    start = prev = None
    for n in nums:
        if start is None:
            start = prev = n
            continue
        if n == prev + 1:
            prev = n
        else:
            parts.append(str(start) if start == prev
                         else "%d-%d" % (start, prev))
            start = prev = n
    if start is not None:
        parts.append(str(start) if start == prev
                     else "%d-%d" % (start, prev))
    return ", ".join(parts)


# ---------------------------------------------------- Einladungs-Events --

def invitations(state, races, tiers=None):
    """Einladungs-Events (Vorbild Project CARS 2): gute Testrennen in
    fuer die Karriere nicht verfuegbaren Klassen erzeugen eine Einladung
    als Testfahrer - unabhaengig vom Meisterschaftsende.

    Rueckgabe: Liste dicts {class, tier, team, avg_position, races}.
    """
    out = []
    active = active_championship(state)
    active_cls = active["vehicle_class"] if active else ""
    current = (state.get("current_class") or "").strip()
    accepted = {inv.get("class") for inv in state.get("invitations") or []}
    for cls, rep in sorted(test_reports(state, races).items()):
        if not cls or cls == active_cls or cls == current \
                or cls in accepted:
            continue
        if rep["races"] >= 1 and rep["avg_position"] <= TEST_AVG_POS:
            strength = 4 if rep["avg_position"] <= 1.5 else 3
            out.append({
                "class": cls,
                "tier": tier_of(cls, tiers),
                "team": team_for_tier(tier_of(cls, tiers), strength),
                "strength": strength,
                "avg_position": rep["avg_position"],
                "races": rep["races"],
            })
    return out


def accept_invitation(state, vehicle_class, races, tiers=None):
    """Nimmt eine Einladung an: neuer Kontrakt in dieser Klasse."""
    cls = (vehicle_class or "").strip()
    for inv in invitations(state, races, tiers):
        if inv["class"] == cls:
            record = {"class": cls, "team": inv["team"],
                      "strength": inv["strength"]}
            state.setdefault("invitations", []).append(record)
            state["current_class"] = cls
            state["current_team"] = inv["team"]
            return record
    raise CareerModeError("Keine gueltige Einladung fuer %s." % cls)


# ------------------------------------------------------- Meisterschaft --

def active_championship(state):
    for c in state["championships"]:
        if c.get("status") == "aktiv":
            return c
    return None


def last_championship(state):
    champs = [c for c in state["championships"]
              if c.get("status") != "aktiv"]
    return champs[-1] if champs else None


def start_championship(state, name, vehicle_class,
                       planned_races=DEFAULT_PLANNED_RACES, tiers=None):
    """Legt eine neue Meisterschaft an (nur eine gleichzeitig aktiv)."""
    if active_championship(state):
        raise CareerModeError(
            "Es laeuft bereits eine aktive Meisterschaft.")
    cls = (vehicle_class or "").strip()
    if not cls:
        raise CareerModeError("Bitte eine Fahrzeugklasse waehlen.")
    if state["championships"]:
        t = tier_of(cls, tiers)
        unlocked = unlocked_tiers(state, tiers)
        if t not in unlocked:
            raise CareerModeError(
                "Klassen-Stufe %d ist noch nicht freigeschaltet"
                " (frei: %s). Aufstieg ueber Angebote, Einladungen"
                " oder eine starke Saison." % (t, tier_ranges(unlocked)))
    champ = {
        "id": state["next_id"],
        "name": (name or "").strip() or "Meisterschaft %d" % state["next_id"],
        "vehicle_class": cls,
        "tier": tier_of(cls, tiers),
        "planned_races": max(1, int(planned_races)),
        "session_ids": [],
        "status": "aktiv",
        "points": 0,
        "rating": None,
        "position": None,
        "offers": [],
    }
    state["next_id"] += 1
    state["championships"].append(champ)
    if not state.get("current_class"):
        state["current_class"] = cls
    return champ


def _used_sessions(state):
    used = set()
    for c in state["championships"]:
        for sid in c.get("session_ids") or []:
            used.add(sid)
    return used


def assign_races(state, races):
    """Ordnet passende Rennen der aktiven Meisterschaft zu.

    races: Objekte mit session_id und vehicle_class (RaceEvent).
    Rueckgabe: Anzahl neu zugeordneter Rennen.
    """
    champ = active_championship(state)
    if champ is None:
        return 0
    used = _used_sessions(state)
    added = 0
    for r in races:
        if len(champ["session_ids"]) >= champ["planned_races"]:
            break
        sid = r.session_id
        if sid in used:
            continue
        if (r.vehicle_class or "").strip() != champ["vehicle_class"]:
            continue
        champ["session_ids"].append(sid)
        used.add(sid)
        added += 1
    return added


def refresh(state, races, standings_for=None):
    """Ordnet Rennen zu und schliesst die Meisterschaft bei Erreichen
    der Rennanzahl ab (inkl. Angebotserzeugung).

    standings_for(session_ids) -> Punktetabelle der Sitzungen (optional,
    z. B. career.standings_for). Rueckgabe: (added, abgeschlossene_Champ).
    """
    added = assign_races(state, races)
    champ = active_championship(state)
    if champ is not None and \
            len(champ["session_ids"]) >= champ["planned_races"]:
        finish_championship(state, champ, races, standings_for)
        return added, champ
    return added, None


def finish_championship(state, champ, races, standings_for=None):
    ids = set(champ["session_ids"])
    mine = [r for r in races if r.session_id in ids]
    points = sum(r.points for r in mine)
    n = max(1, len(mine))
    champ["status"] = "abgeschlossen"
    champ["points"] = points
    champ["rating"] = round(points / (MAX_POSSIBLE_POINTS * n), 4)
    if standings_for:
        try:
            rows = standings_for(list(ids))
            for i, a in enumerate(rows, 1):
                if a.get("is_player"):
                    champ["position"] = i
                    break
        except Exception:
            champ["position"] = None
    champ["offers"] = generate_offers(state, champ, races)
    return champ


# ------------------------------------------------------------ Angebote --

def _offer(state, typ, vehicle_class, strength, champ):
    o = {
        "id": state["next_id"],
        "type": typ,
        "class": vehicle_class,
        "team": team_for_tier(tier_of(vehicle_class), strength),
        "strength": int(strength),
        "championship_id": champ["id"],
        "status": "offen",
    }
    state["next_id"] += 1
    return o


def generate_offers(state, champ, races):
    """Erzeugt das Angebotspaket am Ende einer Meisterschaft.

    - Punkteanteil >= 45 %: Aufstiegsangebot aus der naechsthoeheren
      Stufe (falls vorhanden) zusaetzlich zum Topteam der eigenen Klasse.
    - 25-45 %: zwei Team-Angebote der eigenen Klasse (Spitzenteams).
    - < 25 %: Abstiegsangebot aus der naechsttieferen Stufe (falls
      vorhanden) sowie ein schwaches Team der eigenen Klasse.
    - Testrennen (nicht zugeordnete Rennen) in anderen Klassen mit
      Durchschnittsposition <= 3: zusaetzliches Angebot dieser Klasse.
    """
    offers = []
    tier = champ.get("tier") or tier_of(champ["vehicle_class"])
    ratio = champ.get("rating") or 0.0
    # Aufstieg
    if ratio >= PROMOTION_RATIO:
        higher = classes_of_tier(tier + 1)
        if higher:
            offers.append(_offer(state, "Aufstieg", higher[0], 4, champ))
    # Eigene Klasse
    if ratio >= PROMOTION_RATIO:
        offers.append(_offer(state, "Verbleib", champ["vehicle_class"],
                            4, champ))
        offers.append(_offer(state, "Verbleib", champ["vehicle_class"],
                            3, champ))
    elif ratio >= RELEGATION_RATIO:
        offers.append(_offer(state, "Verbleib", champ["vehicle_class"],
                            3, champ))
        offers.append(_offer(state, "Verbleib", champ["vehicle_class"],
                            2, champ))
    else:
        offers.append(_offer(state, "Verbleib", champ["vehicle_class"],
                            1, champ))
        lower = classes_of_tier(tier - 1)
        if tier > 1 and lower:
            offers.append(_offer(state, "Abstieg", lower[0], 3, champ))
    # Testrennen anderer Klassen
    for cls, rep in test_reports(state, races).items():
        if not cls or cls == champ["vehicle_class"]:
            continue
        if rep["races"] >= 1 and rep["avg_position"] <= TEST_AVG_POS:
            strength = 4 if rep["avg_position"] <= 1.5 else 3
            offers.append(_offer(state, "Testfahrer", cls, strength, champ))
    return offers


def open_offers(state):
    """Alle offenen Angebote (absteigend nach Neuartigkeit)."""
    out = []
    for c in reversed(state["championships"]):
        for o in c.get("offers") or []:
            if o.get("status", "offen") == "offen":
                out.append(o)
    return out


def accept_offer(state, offer_id):
    """Nimmt ein Angebot an; alle weiteren offenen Angebote desselben
    Meisterschaftsalters werden damit abgelehnt."""
    for c in state["championships"]:
        for o in c.get("offers") or []:
            if o.get("id") == offer_id:
                o["status"] = "angenommen"
                for other in c.get("offers") or []:
                    if other is not o and \
                            other.get("status", "offen") == "offen":
                        other["status"] = "abgelehnt"
                state["current_class"] = o["class"]
                state["current_team"] = o["team"]
                return o
    raise CareerModeError("Angebot nicht gefunden.")


def decline_offer(state, offer_id):
    for c in state["championships"]:
        for o in c.get("offers") or []:
            if o.get("id") == offer_id:
                o["status"] = "abgelehnt"
                return o
    raise CareerModeError("Angebot nicht gefunden.")


# --------------------------------------------------------- Testrennen --

def test_reports(state, races):
    """Testrennen = Rennen, die keiner Meisterschaft zugeordnet sind.

    Rueckgabe {klasse: {races, avg_position, best_position}}.
    """
    used = _used_sessions(state)
    agg = {}
    for r in races:
        if r.session_id in used:
            continue
        cls = (r.vehicle_class or "").strip()
        if not cls or not r.position:
            continue
        a = agg.setdefault(cls, {"races": 0, "pos_sum": 0, "best": 0})
        a["races"] += 1
        a["pos_sum"] += r.position
        a["best"] = r.position if a["best"] == 0 \
            else min(a["best"], r.position)
    return {k: {"races": v["races"],
                "avg_position": round(v["pos_sum"] / v["races"], 2)
                if v["races"] else 0.0,
                "best_position": v["best"]}
            for k, v in agg.items()}
