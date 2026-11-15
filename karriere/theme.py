"""Optik im Stil der Project CARS 2 Karriere-Hubs (RaceRoom-Rot-Akzent).

Gestaltungsprinzipien (Vorbild: Project CARS 2 Karriere-Menue):
- Tiefschwarzer Hintergrund mit Panel-Karten in Karbon-Grau.
- Grosse, kondensierte Typografie: Hub-Titel, Kapitel-Überschriften
  in Grossbuchstaben mit rotem Akzent-Balken darunter.
- Klare Karten-Rahmen (Hub Cards) mit linkem Akzent-Streifen.
- Aktive Reiter und Primaer-Aktionen mit roter Unterstreichung
  bzw. rotem Balken; Statusleiste unten. Akzentfarbe bleibt
  durchgaengig RaceRoom-Rot #e8212b.
"""
RR_RED = "#e8212b"
RR_RED_H = "#ff3a45"
RR_RED_D = "#b31b24"
REC_YELLOW = "#e8c34a"

_PAL = {
    "BG": "#0c0c10", "PANEL": "#15151b", "PANEL2": "#1c1c23", "INPUT": "#101015",
    "LINE": "#2a2a33", "LINE2": "#36363f", "TEXT": "#ecedef", "MUTED": "#8e8e99",
    "BAR": "#09090d", "HOVER": "#22222b", "ACC": RR_RED, "ACC_H": RR_RED_H,
    "ACC_D": RR_RED_D, "SCROLL": "#32323c", "ACC_TXT": "#ff5a63",
    "SEL": "#3a2220", "CARD": "#121218", "HEAD": "#202028",
    "BTN": "#1e1e25", "BTN_H": "#26262f", "BTN_B": "#33333d",
}

_QSS = """
QWidget { font-family: "Bahnschrift", "Segoe UI", "Inter", sans-serif; font-size: 13px; color: @TEXT@; }
QMainWindow, QWidget { background: @BG@; }
QLabel { background: transparent; color: @TEXT@; }
QLabel[plain="true"] { background: transparent; }
QLabel#brandTitle { font-size: 24px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#brandSub, QLabel#hint, QLabel#statusLine { color: @MUTED@; background: transparent; font-size: 12px; }
QLabel#sectionTitle { font-size: 13px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#sectionTitle:disabled { color: @MUTED@; }
QLabel#accentRule { background: @ACC@; border: none; }
QTabWidget::pane { border: none; border-top: 1px solid @LINE@; background: transparent; top: -1px; }
QTabBar { background: @BAR@; }
QTabBar::tab { background: transparent; color: @MUTED@; padding: 9px 18px; margin-right: 2px; border: none; border-bottom: 3px solid transparent; font-weight: 800; font-size: 12px; }
QTabBar::tab:hover { color: @TEXT@; border-bottom: 3px solid @LINE2@; }
QTabBar::tab:selected { color: @TEXT@; border-bottom: 3px solid @ACC@; }
QPushButton { background: @BTN@; color: @TEXT@; border: 1px solid @BTN_B@; padding: 8px 16px; border-radius: 2px; font-weight: 700; }
QPushButton:hover { border-color: #4a4a55; background: @BTN_H@; }
QPushButton:pressed { background: @BG@; }
QPushButton:disabled { color: @MUTED@; background: @PANEL@; border-color: @LINE@; }
QPushButton#primary { background: @ACC@; color: #ffffff; border: 1px solid @ACC_D@; padding: 9px 20px; }
QPushButton#primary:hover { background: @ACC_H@; border-color: @ACC_H@; }
QPushButton#primary:pressed { background: @ACC_D@; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: @INPUT@; color: @TEXT@; border: 1px solid @LINE@; border-radius: 2px; selection-background-color: @ACC@; selection-color: #ffffff; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid @ACC_D@; }
QDateEdit, QTimeEdit { background: @INPUT@; color: #ffffff; border: 1px solid @LINE@; border-radius: 2px; padding: 3px 10px; selection-background-color: @ACC@; selection-color: #ffffff; }
QDateEdit:focus, QTimeEdit:focus { border: 1px solid @ACC_D@; }
QDateEdit::up-button, QDateEdit::down-button, QTimeEdit::up-button, QTimeEdit::down-button { background: @PANEL2@; border: none; width: 18px; }
QDateEdit::up-button:hover, QDateEdit::down-button:hover, QTimeEdit::up-button:hover, QTimeEdit::down-button:hover { background: @ACC@; }
QCalendarWidget { background: @PANEL@; font-size: 10pt; }
QCalendarWidget #qt_calendar_navigationbar { background: @HEAD@; }
QCalendarWidget #qt_calendar_prevbutton, QCalendarWidget #qt_calendar_nextbutton { background: @BTN@; border: 1px solid @LINE@; min-width: 28px; min-height: 22px; }
QCalendarWidget #qt_calendar_prevbutton:hover, QCalendarWidget #qt_calendar_nextbutton:hover { background: @ACC@; border-color: @ACC_D@; }
QCalendarWidget #qt_calendar_monthbutton, QCalendarWidget #qt_calendar_yearbutton { background: transparent; color: @TEXT@; font-weight: 600; }
QCalendarWidget #qt_calendar_calendarview { background: @PANEL@; color: #ffffff; alternate-background-color: @PANEL2@; selection-background-color: @ACC@; selection-color: #ffffff; outline: 0; }
QComboBox { padding: 3px 30px 3px 10px; min-height: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: right center; width: 26px; border: none; border-left: 1px solid @LINE@; background: @PANEL2@; }
QComboBox::drop-down:hover { background: @ACC@; }
QComboBox::down-arrow { image: none; width: 1px; }
QComboBox QAbstractItemView { background: @PANEL@; color: @TEXT@; selection-background-color: @ACC@; selection-color: #ffffff; outline: 0; border: 1px solid @LINE2@; padding: 2px; }
QTableView, QTableWidget { background: @PANEL@; color: @TEXT@; gridline-color: #22222a; border: 1px solid @LINE@; border-radius: 0; selection-background-color: @SEL@; selection-color: @TEXT@; }
QTableView::item, QTableWidget::item { padding: 5px 10px; border: 0; }
QTableView::item:hover, QTableWidget::item:hover { background: @HOVER@; }
QTableView::item:selected, QTableWidget::item:selected { background: @SEL@; color: @TEXT@; }
QHeaderView::section { background: @HEAD@; color: @MUTED@; padding: 7px 10px; border: none; border-right: 1px solid @LINE@; border-bottom: 1px solid @ACC_D@; font-size: 11px; font-weight: 800; }
QFrame#kpiCard, QFrame#hubCard, QWidget#chartCard { background: @CARD@; border: 1px solid @LINE@; border-left: 3px solid @ACC@; border-radius: 2px; }
QFrame#hubCardPlain { background: @CARD@; border: 1px solid @LINE@; border-radius: 2px; }
QLabel#kpiValue { font-size: 28px; font-weight: 800; background: transparent; }
QLabel#kpiCaption { color: @MUTED@; font-size: 11px; font-weight: 700; background: transparent; }
QLabel#hubTitle { font-size: 15px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#hubBig { font-size: 21px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#hubSub { color: @MUTED@; font-size: 12px; background: transparent; }
QLabel#tierNum { font-size: 20px; font-weight: 800; background: transparent; }
QLabel#tierLabel { font-size: 10px; font-weight: 700; background: transparent; }
QFrame#tierNode { background: @CARD@; border: 1px solid @LINE@; border-radius: 2px; }
QFrame#tierNode[state="active"] { background: @SEL@; border: 1px solid @ACC@; }
QFrame#tierNode[state="open"] { background: @CARD@; border: 1px solid @LINE2@; }
QFrame#tierNode[state="locked"] { background: #0e0e13; border: 1px solid #23232b; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: @SCROLL@; border-radius: 2px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: @ACC@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
QScrollBar::handle:horizontal { background: @SCROLL@; border-radius: 2px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: @ACC@; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu { background: @PANEL@; color: @TEXT@; border: 1px solid @LINE2@; padding: 4px; }
QMenu::item { padding: 8px 24px; border-radius: 0; }
QMenu::item:selected { background: @ACC@; color: #ffffff; }
QMenu::separator { height: 1px; background: @LINE@; margin: 4px 8px; }
QGroupBox { border: 1px solid @BTN_B@; border-radius: 0; margin-top: 14px; padding: 12px; font-weight: 700; background: @CARD@; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: @MUTED@; }
QStatusBar { background: @BAR@; color: @MUTED@; }
QStatusBar::item { border: none; }
QStatusBar QLabel { color: @MUTED@; }
QToolTip { background: @PANEL@; color: @TEXT@; border: 1px solid @LINE2@; padding: 5px; }
QMessageBox { background: @BG@; }
QMessageBox QLabel { color: @TEXT@; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @LINE2@; background: @INPUT@; border-radius: 2px; }
QCheckBox::indicator:checked { background: @ACC@; border-color: @ACC@; }
QDialog { background: @BG@; }
QProgressBar { background: @INPUT@; color: @TEXT@; border: 1px solid @LINE@; border-radius: 2px; text-align: center; font-weight: 700; }
QProgressBar::chunk { background: @ACC@; }
"""


def dark_qss() -> str:
    q = _QSS
    for k, v in _PAL.items():
        q = q.replace("@%s@" % k, v)
    return q


def apply_dark_theme(app):
    """Fusion-Stil + PCARS2-Hub-Stylesheet auf die Anwendung anwenden."""
    app.setStyle("Fusion")
    app.setStyleSheet(dark_qss())
