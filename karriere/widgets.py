"""Zusaetzliche Qt-Widgets fuer das Karriere-Dashboard.

Enthaelt KPI-Karten (grosse Kennzahlen), das Verlaufs-Diagramm
(QPainter-Linienchart ohne zusaetzliche Abhaengigkeiten) und die
Emblem-Helfer fuer Level, Angebote und Erfolge. Qt-abhaengig, daher
bewusst nicht Teil der unit-getesteten Kern-Logik.
"""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QPen, QFont, QPixmap,
                           QLinearGradient, QPainterPath)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSizePolicy,
                                QVBoxLayout, QWidget)

# Embleme: Level-Baender und Angebotsarten (Text-Glyphen, keine Assets)
LEVEL_EMBLEMS = {1: "\u25cb", 2: "\u25c7", 3: "\u25b2",
                 4: "\u2605", 5: "\u2726", 6: "\u265b"}
TIER_EMBLEM = "\u25c8"
ACH_UNLOCKED = "\u2605"   # Stern
ACH_OPEN = "\u2606"       # Konturstern
OFFER_EMBLEMS = {"Aufstieg": "\u25b2", "Abstieg": "\u25bc",
                 "Verbleib": "\u25c6", "Testfahrer": "\u2731"}


def level_emblem(level):
    return LEVEL_EMBLEMS.get(int(level), LEVEL_EMBLEMS[1])


def offer_emblem(typ):
    return OFFER_EMBLEMS.get(typ, "\u25c6")


class KpiCard(QFrame):
    """Karte mit grosser Kennzahl, kleiner Ueberschrift und Akzentbalken."""

    def __init__(self, caption, value="-", emblem="", color="#e8212b",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.NoFrame)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(2)
        accent = QLabel(self)
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: %s; border: none;" % color)
        lay.addWidget(accent)
        self.lbl_value = QLabel(self)
        self.lbl_value.setObjectName("kpiValue")
        lay.addWidget(self.lbl_value)
        self.lbl_caption = QLabel(caption, self)
        self.lbl_caption.setObjectName("kpiCaption")
        self.lbl_caption.setWordWrap(True)
        lay.addWidget(self.lbl_caption)
        self.set_value(value, emblem)

    def set_value(self, value, emblem=""):
        text = str(value)
        if emblem:
            text = "%s  %s" % (text, emblem)
        self.lbl_value.setText(text)

    def set_caption(self, caption):
        self.lbl_caption.setText(caption)

    def sizeHint(self):
        return self.minimumSizeHint()


class TrendChart(QWidget):
    """Einfaches Linien-Diagramm (QPainter, ohne externe Charts-Bibliothek).

    set_series([(name, farbe, [werte]), ...], x_label) zeichnet bis zu
    drei kumulative Kurven mit Gitter, Achsen und Legende.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chartCard")
        self._series = []
        self._x_label = ""
        self.setMinimumHeight(210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_series(self, series, x_label=""):
        self._series = list(series or [])
        self._x_label = x_label
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        card = QColor("#121218")
        line = QColor("#33333d")
        muted = QColor("#9a9aa4")
        frame = QPainterPath()
        frame.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8.0, 8.0)
        p.fillPath(frame, card)
        p.setPen(QPen(line, 1))
        p.drawPath(frame)

        ml, mr, mt, mb = 58, 16, 30, 30
        cw, ch = max(10, w - ml - mr), max(10, h - mt - mb)

        # Legende (oben rechts)
        lx = ml + 6
        p.setFont(QFont("Segoe UI", 8))
        for name, color, _ in self._series:
            p.setPen(QPen(QColor(color), 2))
            p.drawLine(int(lx), int(mt - 14), int(lx + 16), int(mt - 14))
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(lx + 20, mt - 22, 120, 14), Qt.AlignLeft,
                       str(name))
            lx += 44 + 6 * len(str(name))

        if not self._series or not any(s[2] for s in self._series):
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "Keine Daten")
            return

        ymax = 1.0
        for _, _, values in self._series:
            if values:
                ymax = max(ymax, float(max(values)))
        steps = 4
        p.setFont(QFont("Segoe UI", 8))
        for i in range(steps + 1):
            y = mt + ch - i * ch / steps
            p.setPen(QPen(QColor("#26262e"), 1))
            p.drawLine(int(ml), int(y), int(ml + cw), int(y))
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(4, y - 7, ml - 10, 14), Qt.AlignRight,
                       _fmt(ymax * i / steps))

        n = max(len(values) for _, _, values in self._series)
        # X-Achse: Kennzahlen an 5 Ticks
        for i in range(5):
            frac = i / 4.0
            x = ml + frac * cw
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(x - 30, mt + ch + 6, 60, 14), Qt.AlignHCenter,
                       str(max(1, int(round(frac * (n - 1))) + 1)))
        if self._x_label:
            p.drawText(QRectF(ml, mt + ch + 6, cw, 14), Qt.AlignRight,
                        self._x_label)

        # Kurven mit Verlaufsflaeche darunter
        for _, color, values in self._series:
            if len(values) < 1:
                continue
            base = QColor(color)
            pts = []
            for i, v in enumerate(values):
                x = ml + (cw * i / (len(values) - 1 if len(values) > 1 else 1))
                y = mt + ch - (ch * (float(v) / ymax))
                pts.append(QPointF(x, y))
            if len(pts) >= 2:
                area = QPainterPath(QPointF(pts[0].x(), mt + ch))
                for pt in pts:
                    area.lineTo(pt)
                area.lineTo(pts[-1].x(), mt + ch)
                area.closeSubpath()
                grad = QLinearGradient(0, mt, 0, mt + ch)
                fill = QColor(base)
                fill.setAlpha(60)
                grad.setColorAt(0.0, fill)
                fill2 = QColor(base)
                fill2.setAlpha(0)
                grad.setColorAt(1.0, fill2)
                p.setPen(Qt.NoPen)
                p.setBrush(grad)
                p.drawPath(area)
            pen = QPen(base, 2)
            p.setPen(pen)
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
            if pts:
                p.setBrush(base)
                p.drawEllipse(pts[-1], 3.0, 3.0)


def _fmt(v):
    if v >= 1000:
        return "%dk" % int(round(v / 1000.0))
    return str(int(v) if float(v).is_integer() else round(v, 1))




class HubHeader(QWidget):
    """Kopfband im Stil der Project CARS 2 Karriere-Hubs.

    Banner-Karte mit rundem Level-Emblem, grossem Titel und kleiner
    Untertitel-Zeile. set_info(title, sub, badge="") fuellt das Band;
    badge ist ein Emblem-Glyph (Level-Emblem) im runden Feld links.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 10)
        outer.setSpacing(0)
        banner = QFrame(self)
        banner.setObjectName("hubBanner")
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)
        self.lbl_badge = QLabel("", banner)
        self.lbl_badge.setObjectName("emblemBadge")
        self.lbl_badge.setFixedSize(40, 40)
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_badge)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.lbl_title = QLabel("", banner)
        self.lbl_title.setObjectName("hubBig")
        text.addWidget(self.lbl_title)
        self.lbl_sub = QLabel("", banner)
        self.lbl_sub.setObjectName("hubSub")
        text.addWidget(self.lbl_sub)
        lay.addLayout(text, 1)
        outer.addWidget(banner)

    def set_info(self, title, sub="", badge=""):
        self.lbl_badge.setText(str(badge or ""))
        self.lbl_badge.setVisible(bool(badge))
        self.lbl_title.setText(title)
        self.lbl_sub.setText(sub)


def section_label(text):
    """Kapitel-Überschrift mit rotem Akzent-Balken darunter."""
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 6)
    v.setSpacing(4)
    lbl = QLabel(text, box)
    lbl.setObjectName("hubTitle")
    v.addWidget(lbl)
    rule = QLabel(box)
    rule.setObjectName("accentRule")
    rule.setFixedHeight(2)
    rule.setMaximumWidth(180)
    v.addWidget(rule)
    return box


class HubCard(QFrame):
    """Karte mit Ueberschriften-Band (linker Akzent-Streifen via QSS)."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("hubCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(6)
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setObjectName("hubSub")
        lay.addWidget(self.lbl_title)
        self.body = QVBoxLayout()
        self.body.setSpacing(4)
        lay.addLayout(self.body)

    def set_title(self, title):
        self.lbl_title.setText(title)


class TierLadder(QWidget):
    """Stufenleiter als Knotenreihe (Vorbild: Project CARS 2 Tier-Pfad).

    set_tiers([(stufe, emblem, [klassen], zustand), ...]) mit zustand in
    {"locked", "open", "active"}; zeichnet je Stufe eine Karte mit
    Stufen-Nummer, Emblem und Statusfarbe.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(6)
        self._lay.addStretch(1)
        self._nodes = []

    def clear(self):
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._nodes = []

    def set_tiers(self, tiers):
        """tiers: [(stufe, status, klassen_text), ...] Status wie oben."""
        self.clear()
        for stufe, status, klassen in tiers:
            node = QFrame(self)
            node.setObjectName("tierNode")
            node.setProperty("state", status)
            node.setFixedHeight(76)
            lay = QVBoxLayout(node)
            lay.setContentsMargins(10, 6, 10, 6)
            lay.setSpacing(0)
            head = QHBoxLayout()
            head.setSpacing(6)
            num = QLabel(str(stufe), node)
            num.setObjectName("tierNum")
            if status == "locked":
                num.setStyleSheet("color: #55555f;")
            elif status == "active":
                num.setStyleSheet("color: #ff5a63;")
            else:
                num.setStyleSheet("color: #ecedef;")
            head.addWidget(num)
            emblem = QLabel(TIER_EMBLEM, node)
            emblem.setObjectName("tierLabel")
            emblem.setStyleSheet("font-size: 14px;")
            head.addWidget(emblem)
            head.addStretch(1)
            lay.addLayout(head)
            label = QLabel(klassen, node)
            label.setObjectName("tierLabel")
            label.setWordWrap(True)
            if status == "locked":
                label.setStyleSheet("color: #55555f;")
            else:
                label.setStyleSheet("color: #8e8e99;")
            lay.addWidget(label)
            self._lay.insertWidget(self._lay.count() - 1, node, 1)
            self._nodes.append(node)


# Klassen-Embleme: deterministische Farbe je Fahrzeugklasse;
# Badges werden zur Laufzeit mit QPainter gezeichnet (keine Assets).
CLASS_COLORS = ["#e05260", "#4f8dfd", "#3fbf8f", "#e0a13f", "#a06fe0",
                "#d06fd0", "#5ecfe8", "#8fd05e", "#e8734f", "#7f8fe0"]


def class_color(cls):
    """Stabile Farbe fuer eine Fahrzeugklasse."""
    name = "".join(ch for ch in str(cls or "?").upper() if ch.isalnum())
    return CLASS_COLORS[sum(ord(c) for c in name) % len(CLASS_COLORS)]


def class_initials(cls):
    """Bis zu drei Grossbuchstaben/Ziffern als Klassen-Kuerzel."""
    name = "".join(ch for ch in str(cls or "?").upper() if ch.isalnum())
    return name[:3] or "?"


def class_badge_pixmap(cls, size=24):
    """Runde Klassen-Kachel (Farbe + Kuerzel) als QPixmap."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    color = QColor(class_color(cls))
    edge = QColor(color)
    edge.setAlpha(140)
    p.setBrush(color)
    p.setPen(QPen(edge, 1))
    r = max(3.0, size * 0.30)
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), r, r)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", max(6, int(size * 0.36)), QFont.Bold))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter,
               class_initials(cls))
    p.end()
    return pm
