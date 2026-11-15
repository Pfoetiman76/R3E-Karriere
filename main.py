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
    QMessageBox, QInputDialog, QPushButton, QDialog, QComboBox, QSpinBox,
    QFormLayout, QDialogButtonBox, QLineEdit)
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from karriere import appsettings, careerstate, core, paths, theme
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
        m.addSeparator()
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
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("")

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
        v.addWidget(self.xp_bar)

        self.tbl_tiles = QTableWidget(0, 0)
        v.addWidget(self.tbl_tiles, 2)

        self.lbl_history = QLabel("Rennhistorie")
        self.lbl_history.setObjectName("sectionTitle")
        v.addWidget(self.lbl_history)
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
        w = QWidget()
        v = QVBoxLayout(w)
        self.lbl_contract = QLabel("")
        self.lbl_contract.setObjectName("brandTitle")
        v.addWidget(self.lbl_contract)
        self.lbl_tier = QLabel("")
        self.lbl_tier.setObjectName("brandSub")
        v.addWidget(self.lbl_tier)

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

        self.lbl_champ = QLabel("")
        self.lbl_champ.setWordWrap(True)
        v.addWidget(self.lbl_champ)

        lbl_offers = QLabel("Angebote")
        lbl_offers.setObjectName("sectionTitle")
        v.addWidget(lbl_offers)
        self.tbl_offers = QTableWidget(0, 5)
        self.tbl_offers.setHorizontalHeaderLabels(
            ["Typ", "Klasse", "Team", "Staerke", "Status"])
        self.tbl_offers.horizontalHeader().setStretchLastSection(True)
        self.tbl_offers.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.tbl_offers, 2)

        lbl_tests = QLabel("Testrennen (nicht zugeordnete Rennen;"
                          " gute Ergebnisse verbessern die Angebote)")
        lbl_tests.setObjectName("sectionTitle")
        v.addWidget(lbl_tests)
        self.tbl_tests = QTableWidget(0, 4)
        self.tbl_tests.setHorizontalHeaderLabels(
            ["Klasse", "Rennen", "Position im Schnitt", "Beste Position"])
        self.tbl_tests.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_tests, 1)
        return w

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
        cls = state.get("current_class") or ""
        team = state.get("current_team") or ""
        self.lbl_contract.setText(
            "Kontrakt: %s%s" % (team or "-",
                                (" - " + cls) if cls else ""))
        self.lbl_tier.setText(
            "Klassen-Stufe: %d" % careerstate.tier_of(
                cls, self.settings.get("class_tiers")) if cls
            else "Noch kein Kontrakt - bitte eine Meisterschaft anlegen")

        champ = careerstate.active_championship(state)
        if champ:
            self.lbl_champ.setText(
                "Meisterschaft: %s (%s, Stufe %d) - %d / %d Rennen"
                " zugeordnet" % (
                    champ["name"], champ["vehicle_class"], champ["tier"],
                    len(champ["session_ids"]), champ["planned_races"]))
        else:
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

        offers = careerstate.open_offers(state)
        t = self.tbl_offers
        t.setRowCount(len(offers))
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i, o in enumerate(offers):
            vals = [o["type"], o["class"], o["team"],
                    careerstate.strength_label(o["strength"]),
                    "Offen"]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if c == 0:
                    item.setData(Qt.UserRole, o["id"])
                t.setItem(i, c, item)

        if self.career is not None:
            reports = careerstate.test_reports(state, self.career.races())
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
            self.tbl_tiles.setRowCount(0)
            self.tbl_races.setRowCount(0)
            self.tbl_standings.setRowCount(0)
            self.tbl_ach.setRowCount(0)
            self.tbl_offers.setRowCount(0)
            self.tbl_tests.setRowCount(0)
            self.lbl_contract.setText("Keine Karriere-Daten")
            self.lbl_tier.setText("")
            self.lbl_champ.setText("")
            self.statusBar().showMessage("Keine Ergebnis-Datenbank gefunden")
            return
        # Karriere-Modus: Rennen zuordnen, Abschluss pruefen, speichern
        try:
            added, finished = careerstate.refresh(
                self.state, career.races(), career.standings_for)
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
        self._fill_tiles(stats)
        self._fill_races(career)
        self._fill_standings(career)
        self._fill_achievements(career)
        self.statusBar().showMessage(
            "Datenbank: %s - %d Rennen gewertet" % (db, stats["races"]))

    # ---------------------------------------------------------- Fuellung --

    def _fill_tiles(self, s):
        tiles = [("Rennen", s["races"]), ("Siege", s["wins"]),
                 ("Podien", s["podiums"]), ("Pole", s["poles"]),
                 ("Schnellste Runden", s["fastest_laps"]),
                 ("Punkte gesamt", s["points"]), ("Ziele", s["finishes"]),
                 ("Ausfaelle", s["dnfs"]), ("Strecken", s["tracks"]),
                 ("Fahrzeuge", s["vehicles"]), ("XP gesamt", s["xp"]),
                 ("Level", s["level"])]
        cols, rows = 4, (len(tiles) + 3) // 4
        t = self.tbl_tiles
        t.setRowCount(rows)
        t.setColumnCount(cols)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionMode(QTableWidget.NoSelection)
        t.horizontalHeader().setStretchLastSection(True)
        for i, (label, value) in enumerate(tiles):
            r, c = divmod(i, cols)
            item = QTableWidgetItem("%s\n%s" % (label, value))
            item.setTextAlignment(Qt.AlignCenter)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            t.setItem(r, c, item)

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
            vals = [a["title"], a["desc"],
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
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
