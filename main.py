"""R3E Karriere - Karriere-Modus fuer RaceRoom auf Basis von R3E Resultate.

Wertet die Ergebnis-Datenbank von R3E Resultate (results.db) ausschliesslich
lesend aus: alle Rennsitzungen zaehlen automatisch in einer durchgaengigen
Karriere mit Meisterschafts-Punktetabelle, XP-Level und Erfolgen.
"""
import os
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QProgressBar, QFileDialog,
    QScrollArea, QAbstractItemView,
    QMessageBox, QInputDialog, QPushButton, QDialog, QComboBox, QSpinBox,
    QFormLayout, QDialogButtonBox, QLineEdit)
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon
from PySide6.QtCore import Qt, QTimer, QUrl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from karriere import appsettings, careerstate, core, paths, theme, \
    updatecheck
from karriere.widgets import (KpiCard, TrendChart, level_emblem,
                               offer_emblem, ACH_OPEN, ACH_UNLOCKED,
                               TIER_EMBLEM, HubHeader, HubCard,
                               TierLadder, section_label,
                               class_badge_pixmap)
from karriere.models import APP_NAME, APP_VERSION, format_time_ms
from karriere.core import CareerError, XP_PER_LEVEL, level_title


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_dir = paths.default_app_dir()
        self.settings = appsettings.load_settings(
            appsettings.settings_path(self.app_dir))
        self.career = None
        self.setWindowTitle("%s %s" % (APP_NAME, APP_VERSION))
        self.resize(1100, 720)
        self._build_menu()
        self._build_ui()
        QTimer.singleShot(1500, lambda: self.check_updates(True))
        self.reload()

    # ------------------------------------------------------------ Aufbau --

    def _build_menu(self):
        m = self.menuBar().addMenu("&Werkzeuge")
        act_db = QAction("Ergebnis-Datenbank w&aehlen ...", self)
        act_db.triggered.connect(self.choose_db)
        m.addAction(act_db)
        act_drv = QAction("&Fahrernamen festlegen ...", self)
        act_drv.triggered.connect(self.choose_driver)
        m.addAction(act_drv)
        act_tiers = QAction("&Klassen-Stufen bearbeiten ...", self)
        act_tiers.triggered.connect(self.edit_class_tiers)
        m.addAction(act_tiers)
        act_start = QAction("&Karriere-Startdatum festlegen ...", self)
        act_start.triggered.connect(self.set_career_start)
        m.addAction(act_start)
        act_reset = QAction("Karriere &zuruecksetzen ...", self)
        act_reset.triggered.connect(self.reset_career)
        m.addAction(act_reset)
        m.addSeparator()
        act_update = QAction("&Nach Update suchen ...", self)
        act_update.triggered.connect(lambda: self.check_updates(False))
        m.addAction(act_update)
        act_reload = QAction("&Aktualisieren", self)
        act_reload.setShortcut("F5")
        act_reload.triggered.connect(self.reload)
        m.addAction(act_reload)

    def _build_ui(self):
        tabs = QTabWidget()
        self.tab_career = self._build_career_tab()
        self.tab_overview = self._build_overview_tab()
        self.tab_standings = self._build_standings_tab()
        self.tab_achievements = self._build_achievements_tab()
        tabs.addTab(self.tab_career, "Karriere")
        tabs.addTab(self.tab_overview, "Uebersicht")
        tabs.addTab(self.tab_standings, "Meisterschaft")
        tabs.addTab(self.tab_achievements, "Erfolge")
        for t in (self.tbl_races, self.tbl_standings, self.tbl_ach,
                  self.tbl_invites, self.tbl_offers, self.tbl_tests):
            self._style_table(t)
        self.setCentralWidget(tabs)

    @staticmethod
    def _style_table(t):
        """Einheitliches Tabellenbild: Zebra-Zeilen, kein Gitter,
        schreibgeschuetzt, Auswahl ganzer Zeilen."""
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.verticalHeader().setVisible(False)

    def _build_overview_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.lbl_header = QLabel("")
        self.lbl_header.setObjectName("brandTitle")
        v.addWidget(self.lbl_header)
        self.lbl_sub = QLabel("")
        self.lbl_sub.setObjectName("brandSub")
        v.addWidget(self.lbl_sub)
        self.xp_bar = QProgressBar()
        self.xp_bar.setFormat("XP %v / %m zum naechsten Level")
        self.xp_bar.setFixedHeight(16)
        v.addWidget(self.xp_bar)

        # KPI-Kartenreihe (Dashboard-Kennzahlen)
        self.kpi_cards = {}
        kpis = [("level", "Level", "#e8212b"),
                ("races", "Rennen", "#e8e8ec"),
                ("wins", "Siege", "#e8c34a"),
                ("podiums", "Podien", "#e8c34a"),
                ("poles", "Pole", "#9a9aa4"),
                ("fastest", "Schnellste Runden", "#9a9aa4"),
                ("ach", "Erfolge", "#e8c34a")]
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        for key, caption, color in kpis:
            card = KpiCard(caption, color=color)
            card.setMinimumWidth(110)
            self.kpi_cards[key] = card
            kpi_row.addWidget(card, 1)
        v.addLayout(kpi_row)

        v.addWidget(section_label("Karriere-Verlauf (kumulierte Punkte"
                                  " und XP)"))
        self.chart = TrendChart()
        v.addWidget(self.chart, 2)

        v.addWidget(section_label("Rennhistorie"))
        self.tbl_races = QTableWidget(0, 9)
        self.tbl_races.setHorizontalHeaderLabels(
            ["Datum", "Strecke", "Fahrzeug", "Klasse", "Fahrer",
             "Position", "Punkte", "XP", "Status"])
        self.tbl_races.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_races, 3)
        return w

    def _build_standings_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        lbl = QLabel("Punktetabelle (F1-Schema 25-18-15-12-10-8-6-4-2-1,"
                     " + 1 Bonuspunkt fuer die schnellste Rennrunde"
                     " unter den Top 10)")
        lbl.setObjectName("hint")
        v.addWidget(lbl)
        self.tbl_standings = QTableWidget(0, 6)
        self.tbl_standings.setHorizontalHeaderLabels(
            ["Pos.", "Fahrer", "Punkte", "Siege", "Podien", "Rennen"])
        self.tbl_standings.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_standings)
        return w

    def _build_achievements_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        lbl = QLabel("Freigeschaltete Erfolge werden mit dem Renn-Datum"
                     " angezeigt, das den Erfolg erstmals erfuellte.")
        lbl.setObjectName("hint")
        v.addWidget(lbl)
        self.tbl_ach = QTableWidget(0, 5)
        self.tbl_ach.setHorizontalHeaderLabels(
            ["Erfolg", "Beschreibung", "Fortschritt", "Status",
             "Freigeschaltet"])
        self.tbl_ach.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_ach)
        return w

    # ------------------------------------------------- Karriere-Modus --

    def _build_career_tab(self):
        """Karriere-Hub im Stil der Project CARS 2 Karrierezentrale:
        Kopfband mit Rang, Stufenleiter als Knotenreihe, Kontrakt- und
        Meisterschafts-Karte, darunter Einladungen, Angebote, Testrennen."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 18)
        v.setSpacing(10)

        self.career_header = HubHeader()
        v.addWidget(self.career_header)

        v.addWidget(section_label("Klassen-Stufen"))
        self.tier_ladder = TierLadder()
        v.addWidget(self.tier_ladder)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_contract = HubCard("Kontrakt")
        self.lbl_contract = QLabel("")
        self.lbl_contract.setObjectName("hubTitle")
        self.lbl_contract.setWordWrap(True)
        self.lbl_tier = QLabel("")
        self.lbl_tier.setObjectName("hubSub")
        self.lbl_tier.setWordWrap(True)
        self.card_contract.body.addWidget(self.lbl_contract)
        self.card_contract.body.addWidget(self.lbl_tier)
        cards.addWidget(self.card_contract, 1)

        self.card_champ = HubCard("Meisterschaft")
        self.lbl_champ = QLabel("")
        self.lbl_champ.setWordWrap(True)
        self.champ_bar = QProgressBar()
        self.champ_bar.setFormat("Meisterschaft: %v / %m Rennen")
        self.champ_bar.setFixedHeight(16)
        self.card_champ.body.addWidget(self.lbl_champ)
        self.card_champ.body.addWidget(self.champ_bar)
        cards.addWidget(self.card_champ, 1)
        v.addLayout(cards)

        row = QHBoxLayout()
        self.btn_new_champ = QPushButton("Meisterschaft anlegen ...")
        self.btn_new_champ.setObjectName("primary")
        self.btn_new_champ.clicked.connect(self.new_championship)
        row.addWidget(self.btn_new_champ)
        self.btn_accept = QPushButton("Angebot annehmen")
        self.btn_accept.clicked.connect(self.accept_offer)
        row.addWidget(self.btn_accept)
        self.btn_decline = QPushButton("Angebot ablehnen")
        self.btn_decline.clicked.connect(self.decline_offer)
        row.addWidget(self.btn_decline)
        row.addStretch(1)
        v.addLayout(row)

        v.addWidget(section_label("Einladungs-Events (gute Testrennen"
                                  " in fremden Klassen)"))
        inv_row = QHBoxLayout()
        self.tbl_invites = QTableWidget(0, 4)
        self.tbl_invites.setHorizontalHeaderLabels(
            ["Klasse", "Stufe", "Team", "Pos. im Schnitt"])
        self.tbl_invites.horizontalHeader().setStretchLastSection(True)
        self.tbl_invites.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_invites.setMaximumHeight(140)
        inv_row.addWidget(self.tbl_invites, 1)
        inv_btns = QVBoxLayout()
        self.btn_accept_inv = QPushButton("Einladung annehmen")
        self.btn_accept_inv.clicked.connect(self.accept_invitation)
        inv_btns.addWidget(self.btn_accept_inv)
        inv_btns.addStretch(1)
        inv_row.addLayout(inv_btns)
        v.addLayout(inv_row)

        v.addWidget(section_label("Angebote"))
        self.tbl_offers = QTableWidget(0, 5)
        self.tbl_offers.setHorizontalHeaderLabels(
            ["Typ", "Klasse", "Team", "Staerke", "Status"])
        self.tbl_offers.horizontalHeader().setStretchLastSection(True)
        self.tbl_offers.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.tbl_offers, 2)

        v.addWidget(section_label("Testrennen (nicht zugeordnete Rennen;"
                                  " gute Ergebnisse verbessern die"
                                  " Angebote)"))
        self.tbl_tests = QTableWidget(0, 4)
        self.tbl_tests.setHorizontalHeaderLabels(
            ["Klasse", "Rennen", "Position im Schnitt", "Beste Position"])
        self.tbl_tests.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_tests, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(w)
        return scroll

    def _career_classes(self):
        """Klassen-Vorschlaege: bekannte Rennklassen + Hierarchie."""
        classes = set()
        if self.career is not None:
            for r in self.career.races():
                if r.vehicle_class:
                    classes.add(r.vehicle_class)
        classes.update(careerstate.DEFAULT_CLASS_TIERS.keys())
        return sorted(classes)

    def new_championship(self):
        if self.career is None:
            QMessageBox.information(
                self, "Meisterschaft",
                "Zunaechst eine gueltige Ergebnis-Datenbank oeffnen.")
            return
        state = getattr(self, "state", None)
        if state and careerstate.active_championship(state):
            QMessageBox.information(
                self, "Meisterschaft",
                "Es laeuft bereits eine aktive Meisterschaft. Diese wird"
                " erst nach der festgelegten Rennanzahl abgeschlossen.")
            return
        classes = self._career_classes()
        if self.state.get("championships"):
            unlocked = careerstate.unlocked_tiers(
                self.state, self.settings.get("class_tiers"))
            classes = [c for c in classes
                       if careerstate.tier_of(
                           c, self.settings.get("class_tiers"))
                       in unlocked]
            if not classes:
                QMessageBox.information(
                    self, "Meisterschaft",
                    "Keine freigeschaltete Klasse verfuegbar. Aufstieg"
                    " ueber Angebote, Einladungen oder eine starke"
                    " Saison.")
                return
        if not classes:
            QMessageBox.information(
                self, "Meisterschaft",
                "Keine Fahrzeugklassen gefunden.")
            return
        cls, ok = QInputDialog.getItem(
            self, "Meisterschaft anlegen", "Fahrzeugklasse:", classes,
            0, False)
        if not ok or not cls:
            return
        name, ok = QInputDialog.getText(
            self, "Meisterschaft anlegen",
            "Name der Meisterschaft:", text="%s-Saison" % cls)
        if not ok:
            return
        planned, ok = QInputDialog.getInt(
            self, "Meisterschaft anlegen", "Geplante Rennanzahl:",
            careerstate.DEFAULT_PLANNED_RACES, 1, 100, 1)
        if not ok:
            return
        try:
            careerstate.start_championship(
                self.state, name, cls, planned,
                self.settings.get("class_tiers"))
        except careerstate.CareerModeError as exc:
            QMessageBox.warning(self, "Meisterschaft", str(exc))
            return
        careerstate.save_state(self._state_path, self.state)
        self.reload()

    def accept_offer(self):
        self._offer_action(careerstate.accept_offer, "annehmen")

    def decline_offer(self):
        self._offer_action(careerstate.decline_offer, "ablehnen")

    def _offer_action(self, func, verb):
        row = self.tbl_offers.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Angebote", "Bitte zunaechst ein Angebot auswaehlen.")
            return
        offer_id = self.tbl_offers.item(row, 0).data(Qt.UserRole)
        try:
            func(self.state, offer_id)
        except careerstate.CareerModeError as exc:
            QMessageBox.warning(self, "Angebote", str(exc))
            return
        careerstate.save_state(self._state_path, self.state)
        self.reload()

    def check_updates(self, silent=True):
        """Prueft das neueste GitHub-Release gegen APP_VERSION."""
        info = updatecheck.fetch_latest()
        if info is None:
            if not silent:
                QMessageBox.information(
                    self, "Update",
                    "Der Update-Server ist derzeit nicht erreichbar.")
            return
        if not updatecheck.is_newer(info["tag"], APP_VERSION):
            if not silent:
                QMessageBox.information(
                    self, "Update",
                    "R3E Karriere ist auf dem neuesten Stand (%s)."
                    % APP_VERSION)
            return
        box = QMessageBox(self)
        box.setWindowTitle("Update verfuegbar")
        box.setIcon(QMessageBox.Information)
        box.setText("Version %s ist verfuegbar (installiert: %s)."
                    % (info["tag"].lstrip("vV"), APP_VERSION))
        if info["exe_url"]:
            btn_dl = box.addButton("Installer herunterladen",
                                   QMessageBox.AcceptRole)
        btn_web = box.addButton("Release-Seite oeffnen",
                                QMessageBox.ActionRole)
        box.addButton("Spaeter", QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if info["exe_url"] and clicked is btn_dl:
            self._download_update(info["exe_url"])
        elif clicked is btn_web:
            QDesktopServices.openUrl(QUrl(info["url"] or
                                          "https://github.com/Pfoetiman76"
                                          "/R3E-Karriere/releases"))

    def _download_update(self, url):
        """Laedt den Setup-Installer in den Downloads-Ordner."""
        import urllib.request
        try:
            os.makedirs(os.path.join(os.path.expanduser("~"),
                                     "Downloads"), exist_ok=True)
            target = os.path.join(
                os.path.expanduser("~"), "Downloads",
                os.path.basename(url))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            urllib.request.urlretrieve(url, target)
            QApplication.restoreOverrideCursor()
            ret = QMessageBox.question(
                self, "Update",
                "Installer gespeichert:\n%s\n\nJetzt starten?"
                % target)
            if ret == QMessageBox.Yes and os.name == "nt":
                os.startfile(target)  # noqa: Windows: Installer starten
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Update",
                                "Download fehlgeschlagen: %s" % exc)

    def accept_invitation(self):
        if self.career is None:
            return
        row = self.tbl_invites.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Einladungen",
                "Bitte zunaechst eine Einladung auswaehlen.")
            return
        cls = self.tbl_invites.item(row, 0).text()
        career_races = careerstate.filter_races_from(
            self.career.races(), self.settings.get("career_start"))
        try:
            careerstate.accept_invitation(
                self.state, cls, career_races,
                self.settings.get("class_tiers"))
        except careerstate.CareerModeError as exc:
            QMessageBox.warning(self, "Einladungen", str(exc))
            return
        careerstate.save_state(self._state_path, self.state)
        self.reload()

    def set_career_start(self):
        """Ab diesem Datum (YYYY-MM-DD) zaehlen Rennen im Karriere-Modus."""
        current = self.settings.get("career_start") or ""
        text, ok = QInputDialog.getText(
            self, "Karriere-Startdatum",
            "Nur Rennen ab diesem Datum zaehlen (YYYY-MM-DD,"
            " leer = alle Rennen):", text=current)
        if not ok:
            return
        value = text.strip()
        if value and not appsettings._clean_career_start(value):
            QMessageBox.warning(
                self, "Karriere-Startdatum",
                "Bitte ein Datum im Format JJJJ-MM-TT angeben"
                " oder das Feld leer lassen.")
            return
        self.settings["career_start"] = \
            appsettings._clean_career_start(value)
        appsettings.save_settings(
            appsettings.settings_path(self.app_dir), self.settings)
        self.reload()

    def reset_career(self):
        """Karriere beenden und von null anfangen.

        Loescht den Karriere-Zustand (karriere.json): Meisterschaften,
        Kontrakte, Angebote, Einladungen und Freischaltungen. Punkte,
        XP und Erfolge werden aus der unveraenderten Ergebnis-Datenbank
        bei der naechsten Aktualisierung neu aufgebaut."""
        ret = QMessageBox.question(
            self, "Karriere zuruecksetzen",
            "Moechten Sie die aktuelle Karriere wirklich beenden und"
            " von null anfangen?\n\n"
            "Alle Meisterschaften, Kontrakte, Angebote, Einladungen"
            " und Freischaltungen werden geloescht.\n\n"
            "Die Renndaten in der Ergebnis-Datenbank von R3E Resultate"
            " bleiben unveraendert; Punkte, XP und Erfolge werden"
            " daraus neu aufgebaut.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            self.state = careerstate.reset_state(self._state_path)
        except OSError as exc:
            QMessageBox.critical(
                self, "Karriere zuruecksetzen",
                "Die Karriere-Datei konnte nicht geschrieben werden:\n"
                "%s" % exc)
            return
        self.statusBar().showMessage("Karriere zurueckgesetzt")
        self.reload()

    def edit_class_tiers(self):
        """Einfacher Dialog: Klasse -> Stufe (1 = langsamste, 6 = schnellste)."""
        merged = careerstate.merged_tiers(self.settings.get("class_tiers"))
        classes = set(merged.keys())
        if self.career is not None:
            classes.update(
                r.vehicle_class for r in self.career.races()
                if r.vehicle_class)
        dlg = QDialog(self)
        dlg.setWindowTitle("Klassen-Stufen bearbeiten")
        dlg.resize(420, 520)
        form = QVBoxLayout(dlg)
        form.addWidget(QLabel(
            "Stufe 1 = langsamste Klasse, 6 = schnellste Klasse."
            " Unbekannte Klassen fallen auf Stufe %d zurueck."
            % careerstate.DEFAULT_TIER))
        table = QTableWidget(len(classes), 2)
        table.setHorizontalHeaderLabels(["Klasse", "Stufe"])
        table.horizontalHeader().setStretchLastSection(True)
        for i, cls in enumerate(sorted(classes)):
            item = QTableWidgetItem(cls)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, 0, item)
            spin = QSpinBox()
            spin.setRange(1, 6)
            spin.setValue(merged.get(cls, careerstate.DEFAULT_TIER))
            table.setCellWidget(i, 1, spin)
        form.addWidget(table)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        tiers = {}
        for i in range(table.rowCount()):
            cls = table.item(i, 0).text().strip()
            spin = table.cellWidget(i, 1)
            if cls:
                tiers[cls] = spin.value()
        self.settings["class_tiers"] = tiers
        appsettings.save_settings(
            appsettings.settings_path(self.app_dir), self.settings)
        self.reload()

    def _fill_career(self):
        state = self.state
        if self.career is not None:
            lv = self.career.level()
            unlocked_count = sum(
                1 for a in self.career.achievements() if a["unlocked"])
            total_count = len(self.career.achievements())
            self.career_header.set_info(
                "Level %d - %s" % (lv, core.level_title(lv)),
                "Erfolge: %d / %d  |  Freigeschaltete Stufen: %s" % (
                    unlocked_count, total_count, careerstate.tier_ranges(
                        careerstate.unlocked_tiers(
                            state, self.settings.get("class_tiers")))),
                badge=level_emblem(lv))
        else:
            self.career_header.set_info(
                "Karrieretafel", "Keine Karriere-Daten")
        tiers_cfg = self.settings.get("class_tiers")
        merged = careerstate.merged_tiers(tiers_cfg)
        unlocked = set(careerstate.unlocked_tiers(state, tiers_cfg))
        cls = state.get("current_class") or ""
        current_tier = (careerstate.tier_of(cls, tiers_cfg)
                        if cls else None)
        ladder = []
        for t in range(1, 7):
            names = sorted(c for c, tt in merged.items() if tt == t)
            text = ", ".join(names[:2])
            if len(names) > 2:
                text += " +%d" % (len(names) - 2)
            if not text:
                text = "-"
            if t == current_tier:
                status = "active"
            elif t in unlocked:
                status = "open"
            else:
                status = "locked"
            ladder.append((t, status, text))
        self.tier_ladder.set_tiers(ladder)
        team = state.get("current_team") or ""
        self.lbl_contract.setText(
            "Kontrakt: %s%s" % (team or "-",
                                (" - " + cls) if cls else ""))
        start = self.settings.get("career_start") or ""
        start_info = (" | Rennen ab %s" % start) if start else ""
        if cls:
            tier = careerstate.tier_of(
                cls, self.settings.get("class_tiers"))
            self.lbl_tier.setText(
                "%s  Klassen-Stufe: %d%s" % (TIER_EMBLEM, tier,
                                             start_info))
        else:
            self.lbl_tier.setText(
                "Noch kein Kontrakt - bitte eine Meisterschaft"
                " anlegen%s" % start_info)

        champ = careerstate.active_championship(state)
        if champ:
            self.lbl_champ.setText(
                "Meisterschaft: %s (%s, Stufe %d) - %d / %d Rennen"
                " zugeordnet" % (
                    champ["name"], champ["vehicle_class"], champ["tier"],
                    len(champ["session_ids"]), champ["planned_races"]))
            self.champ_bar.setRange(0, champ["planned_races"])
            self.champ_bar.setValue(len(champ["session_ids"]))
        else:
            self.champ_bar.setRange(0, 1)
            self.champ_bar.setValue(0)
            last = careerstate.last_championship(state)
            if last:
                pos = last.get("position")
                self.lbl_champ.setText(
                    "Letzte Meisterschaft: %s (%s) - %d Punkte, Platz %s,"
                    " Bewertung %d %%" % (
                        last["name"], last["vehicle_class"],
                        last["points"], str(pos) if pos else "-",
                        round(100 * (last.get("rating") or 0))))
            else:
                self.lbl_champ.setText(
                    "Noch keine Meisterschaft angelegt.")

        if self.career is not None:
            career_races = careerstate.filter_races_from(
                self.career.races(), self.settings.get("career_start"))
            invs = careerstate.invitations(
                state, career_races,
                self.settings.get("class_tiers"))
        else:
            invs = []
        ti = self.tbl_invites
        ti.setRowCount(len(invs))
        ti.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, inv in enumerate(invs):
            vals = [inv["class"], "Stufe %d" % inv["tier"],
                    inv["team"], "%.1f" % inv["avg_position"]]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 0:
                    item.setIcon(QIcon(class_badge_pixmap(inv["class"])))
                ti.setItem(i, c, item)

        offers = careerstate.open_offers(state)
        t = self.tbl_offers
        t.setRowCount(len(offers))
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, o in enumerate(offers):
            vals = ["%s  %s" % (offer_emblem(o["type"]), o["type"]),
                    o["class"], o["team"],
                    careerstate.strength_label(o["strength"]),
                    "Offen"]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if c == 0:
                    item.setData(Qt.UserRole, o["id"])
                if c == 1:
                    item.setIcon(QIcon(class_badge_pixmap(o["class"])))
                t.setItem(i, c, item)

        if self.career is not None:
            career_races = careerstate.filter_races_from(
                self.career.races(), self.settings.get("career_start"))
            reports = careerstate.test_reports(state, career_races)
        else:
            reports = {}
        t2 = self.tbl_tests
        t2.setRowCount(len(reports))
        t2.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, (cls_name, rep) in enumerate(
                sorted(reports.items(), key=lambda kv: -kv[1]["races"])):
            vals = [cls_name, str(rep["races"]),
                    "%.1f" % rep["avg_position"], str(rep["best_position"])]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 0:
                    item.setIcon(QIcon(class_badge_pixmap(cls_name)))
                t2.setItem(i, c, item)

    # ---------------------------------------------------------- Aktionen --

    def choose_db(self):
        start = self.settings.get("results_db") or paths.default_results_db()
        start_dir = os.path.dirname(start) if os.path.isfile(start) else start
        path, _ = QFileDialog.getOpenFileName(
            self, "Ergebnis-Datenbank von R3E Resultate waehlen",
            start_dir or "", "SQLite-Datenbank (*.db);;Alle Dateien (*)")
        if not path:
            return
        self.settings["results_db"] = path
        appsettings.save_settings(
            appsettings.settings_path(self.app_dir), self.settings)
        self.reload()

    def choose_driver(self):
        cur = self.settings.get("driver_name") or ""
        name, ok = QInputDialog.getText(
            self, "Fahrernamen festlegen",
            "Eigenen Fahrernamen eingeben (noetig fuer Multiplayer-"
            "Sitzungen; bei Einzelspieler-Rennen wird der eigene Fahrer"
            "automatisch erkannt):", text=cur)
        if not ok:
            return
        self.settings["driver_name"] = name.strip()
        appsettings.save_settings(
            appsettings.settings_path(self.app_dir), self.settings)
        self.reload()

    def reload(self):
        db = self.settings.get("results_db") or paths.default_results_db()
        self._state_path = paths.career_state_path(self.app_dir)
        self.state = careerstate.load_state(self._state_path)
        try:
            from karriere.core import Career
            career = Career(db, self.settings.get("driver_name", ""))
            stats = career.stats()
            self.career = career
        except CareerError as exc:
            self.career = None
            self.lbl_header.setText("Keine Karriere-Daten")
            self.lbl_sub.setText(str(exc).replace("\n", " "))
            self.xp_bar.setRange(0, 1)
            self.xp_bar.setValue(0)
            for card in self.kpi_cards.values():
                card.set_value("-")
            self.chart.set_series([])
            self.champ_bar.setRange(0, 1)
            self.champ_bar.setValue(0)
            self.tbl_races.setRowCount(0)
            self.tbl_standings.setRowCount(0)
            self.tbl_ach.setRowCount(0)
            self.tbl_offers.setRowCount(0)
            self.tbl_tests.setRowCount(0)
            self.lbl_contract.setText("Keine Karriere-Daten")
            self.lbl_tier.setText("")
            self.lbl_champ.setText("")
            self.career_header.set_info("Karrieretafel",
                                        "Keine Karriere-Daten")
            self.tier_ladder.clear()
            self.statusBar().showMessage("Keine Ergebnis-Datenbank gefunden")
            return
        # Karriere-Modus: nur Rennen ab dem Startdatum zaehlen
        career_races = careerstate.filter_races_from(
            career.races(), self.settings.get("career_start"))
        try:
            added, finished = careerstate.refresh(
                self.state, career_races, career.standings_for)
            careerstate.save_state(self._state_path, self.state)
            if finished is not None:
                QMessageBox.information(
                    self, "Meisterschaft abgeschlossen",
                    "Die Meisterschaft %s ist abgeschlossen."
                    " Bitte die neuen Angebote im Reiter Karriere"
                    " pruefen." % finished["name"])
        except careerstate.CareerModeError:
            pass
        self._fill_career()
        drv = career.driver_name_detected()
        self.lbl_header.setText(
            "%s - Level %d (%s)" % (drv or "Fahrer", stats["level"],
                                    level_title(stats["level"])))
        self.lbl_sub.setText(
            "%d Rennen - %d Siege - %d Podien - %d Pole - %d Punkte" % (
                stats["races"], stats["wins"], stats["podiums"],
                stats["poles"], stats["points"]))
        self.xp_bar.setRange(0, XP_PER_LEVEL)
        self.xp_bar.setValue(career.xp_into_level())
        self._fill_dashboard(career, stats)
        self._fill_races(career)
        self._fill_standings(career)
        self._fill_achievements(career)
        self.statusBar().showMessage(
            "Datenbank: %s - %d Rennen gewertet" % (db, stats["races"]))

    # ---------------------------------------------------------- Fuellung --

    def _fill_dashboard(self, career, s):
        """KPI-Karten und Verlaufs-Diagramm des Dashboards fuellen."""
        unlocked = sum(1 for a in career.achievements() if a["unlocked"])
        total = len(career.achievements())
        self.kpi_cards["level"].set_value(s["level"],
                                          level_emblem(s["level"]))
        self.kpi_cards["level"].set_caption(
            core.level_title(s["level"]))
        self.kpi_cards["races"].set_value(s["races"])
        self.kpi_cards["wins"].set_value(s["wins"])
        self.kpi_cards["podiums"].set_value(s["podiums"])
        self.kpi_cards["poles"].set_value(s["poles"])
        self.kpi_cards["fastest"].set_value(s["fastest_laps"])
        self.kpi_cards["ach"].set_value("%d / %d" % (unlocked, total))
        prog = career.progression()
        points = [row["points"] for row in prog]
        xp = [row["xp"] for row in prog]
        self.chart.set_series(
            [("Punkte", "#e8212b", points), ("XP", "#e8c34a", xp)],
            x_label="Rennen")

    def _fill_races(self, career):
        races = list(reversed(career.races()))
        t = self.tbl_races
        t.setRowCount(len(races))
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, r in enumerate(races):
            vals = [r.timestamp, r.track_full, r.vehicle or "-",
                    r.vehicle_class or "-", r.name,
                    str(r.position) if r.position else "-",
                    str(r.points), str(r.xp),
                    "Ziel" if r.finished else "Ausfall"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c in (5, 6, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                if c == 3 and r.vehicle_class:
                    item.setIcon(QIcon(
                        class_badge_pixmap(r.vehicle_class)))
                if c == 5 and r.podium:
                    item.setForeground(QColor("#e8c34a"))
                if c == 8 and not r.finished:
                    item.setForeground(QColor("#ff5a63"))
                t.setItem(i, c, item)

    def _fill_standings(self, career):
        rows = career.standings()
        t = self.tbl_standings
        t.setRowCount(len(rows))
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, a in enumerate(rows):
            vals = [str(i + 1), a["name"], str(a["points"]),
                    str(a["wins"]), str(a["podium"]), str(a["races"])]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(
                    Qt.AlignCenter if c != 1 else Qt.AlignLeft)
                if c == 0 and i < 3:
                    medal = ["#e8c34a", "#c8c8d0", "#b07a4a"][i]
                    item.setForeground(QColor(medal))
                if a["is_player"]:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor("#ff5a63"))
                t.setItem(i, c, item)

    def _fill_achievements(self, career):
        rows = career.achievements()
        t = self.tbl_ach
        t.setRowCount(len(rows))
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, a in enumerate(rows):
            vals = ["%s  %s" % (ACH_UNLOCKED if a["unlocked"] else ACH_OPEN,
                                a["title"]), a["desc"],
                    "%d / %d" % (a["current"], a["goal"]),
                    "Freigeschaltet" if a["unlocked"] else "Offen",
                    a["unlocked"] or "-"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                if a["unlocked"]:
                    item.setForeground(QColor("#e8c34a"))
                elif c == 3:
                    item.setForeground(QColor("#9a9aa4"))
                t.setItem(i, c, item)


def main():
    app = QApplication(sys.argv)
    theme.apply_dark_theme(app)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
