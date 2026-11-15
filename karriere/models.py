"""R3E Karriere - Modelle und Konstanten (Qt-frei)."""
APP_NAME = "R3E Karriere"
APP_VERSION = "0.8.0"


def format_time_ms(ms) -> str:
    """Formatiert Millisekunden als m:ss.mmm; leer fuer ungueltige Werte."""
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return ""
    if ms <= 0:
        return ""
    m, rem = divmod(ms, 60000)
    s, msec = divmod(rem, 1000)
    return f"{m}:{s:02d}.{msec:03d}"
