"""Zusaetzliche Qt-Widgets fuer das Karriere-Dashboard.

Enthaelt KPI-Karten (grosse Kennzahlen), das Verlaufs-Diagramm
(QPainter-Linienchart ohne zusaetzliche Abhaengigkeiten) und die
Emblem-Helfer fuer Level, Angebote und Erfolge. Qt-abhaengig, daher
bewusst nicht Teil der unit-getesteten Kern-Logik.
"""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
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
        card = QColor("#16161c")
        line = QColor("#33333d")
        muted = QColor("#9a9aa4")
        p.fillRect(0, 0, w, h, card)
        p.setPen(QPen(line, 1))
        p.drawRect(0, 0, w - 1, h - 1)

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

        # Kurven
        for _, color, values in self._series:
            if len(values) < 1:
                continue
            pen = QPen(QColor(color), 2)
            p.setPen(pen)
            pts = []
            for i, v in enumerate(values):
                x = ml + (cw * i / (len(values) - 1 if len(values) > 1 else 1))
                y = mt + ch - (ch * (float(v) / ymax))
                pts.append(QPointF(x, y))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
            if pts:
                p.setBrush(QColor(color))
                p.drawEllipse(pts[-1], 3.0, 3.0)


def _fmt(v):
    if v >= 1000:
        return "%dk" % int(round(v / 1000.0))
    return str(int(v) if float(v).is_integer() else round(v, 1))


section_label = _section_label


class HubHeader(QWidget):
    """Kopfband im Stil der Project CARS 2 Karriere-Hubs.

    Grosser Name/Titel, darunter kleine Untertitel-Zeile und ein roter
    Akzent-Balken. set_info(title, sub) fuellt das Band.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 10)
        lay.setSpacing(2)
        self.lbl_title = QLabel("", self)
        self.lbl_title.setObjectName("hubBig")
        lay.addWidget(self.lbl_title)
        self.lbl_sub = QLabel("", self)
        self.lbl_sub.setObjectName("hubSub")
        lay.addWidget(self.lbl_sub)
        rule = QLabel(self)
        rule.setObjectName("accentRule")
        rule.setFixedHeight(3)
        lay.addWidget(rule)

    def set_info(self, title, sub=""):
        self.lbl_title.setText(title)
        self.lbl_sub.setText(sub)


def _section_label(text):
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
            node.setFixedHeight(64)
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
