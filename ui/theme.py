"""Colori, stile globale e funzioni di formattazione condivise da tutta l'interfaccia.

Regola dei colori (uguale in tutta l'app):
  verde  = pagato / incassato
  arancio = da incassare
  rosso  = scaduto / attenzione
  blu    = azioni principali e informazioni neutre
"""
from datetime import date

# --- Palette ---------------------------------------------------------------
BG = "#f3f5f9"
SURFACE = "#ffffff"
BORDER = "#e2e8f0"
BORDER_STRONG = "#cbd5e1"
TEXT = "#0f172a"
TEXT_MUTED = "#64748b"
TEXT_SOFT = "#94a3b8"
SIDEBAR = "#0f172a"
SIDEBAR_HOVER = "#1e293b"

BLUE = "#2563eb"
BLUE_SOFT = "#3b82f6"
GREEN = "#16a34a"
GREEN_DARK = "#15803d"
AMBER = "#f59e0b"
AMBER_DARK = "#92400e"
RED = "#dc2626"
RED_DARK = "#b91c1c"
GREY_BAR = "#cbd5e1"

# Stile delle "pillole" di stato: (sfondo, testo)
PILL = {
    "verde": ("#f0fdf4", "#166534"),
    "arancio": ("#fffbeb", "#92400e"),
    "rosso": ("#fef2f2", "#b91c1c"),
    "grigio": ("#f1f5f9", "#475569"),
    "blu": ("#eff6ff", "#1d4ed8"),
}

MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


# --- Formattazione -----------------------------------------------------------
def fmt_euro(value: float | None, decimali: int = 2) -> str:
    """1234.5 -> '€ 1.234,50' (formato italiano)."""
    value = float(value or 0)
    testo = f"{value:,.{decimali}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {testo}"


def fmt_data(iso: str | None, vuoto: str = "—") -> str:
    """'2026-10-28' -> '28/10/2026'."""
    if not iso:
        return vuoto
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def fmt_data_breve(iso: str | None) -> str:
    """'2026-10-28' -> '28/10'."""
    if not iso:
        return ""
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d/%m")
    except ValueError:
        return str(iso)


def oggi_esteso() -> str:
    oggi = date.today()
    return f"{GIORNI[oggi.weekday()]} {oggi.day} {MESI[oggi.month - 1].lower()} {oggi.year}"


def saluto() -> str:
    from datetime import datetime
    ora = datetime.now().hour
    if ora < 13:
        return "Buongiorno"
    if ora < 18:
        return "Buon pomeriggio"
    return "Buonasera"


def stato_fattura(fattura: dict) -> tuple[str, str]:
    """Restituisce (testo, colore) dell'etichetta di stato da mostrare all'utente."""
    stato = fattura.get("stato")
    if stato == "Pagato":
        quando = fmt_data_breve(fattura.get("data_estinzione"))
        return (f"Pagata {quando}".strip(), "verde")
    scadenza = fattura.get("data_scadenza")
    if scadenza and scadenza < date.today().isoformat():
        return ("Scaduta", "rosso")
    if stato == "Non pagato":
        return ("Non pagata", "rosso")
    return ("Da incassare", "arancio")


def da_sollecitare(fattura: dict) -> bool:
    """Scaduta oppure segnata come insoluta ("Non pagato")."""
    return fattura.get("stato") == "Non pagato" or is_scaduta(fattura)


def is_scaduta(fattura: dict) -> bool:
    return (
        fattura.get("stato") != "Pagato"
        and bool(fattura.get("data_scadenza"))
        and fattura["data_scadenza"] < date.today().isoformat()
    )


# --- Foglio di stile globale --------------------------------------------------
APP_STYLE = f"""
QWidget {{
    color: {TEXT};
    font-size: 14px;
}}
QMainWindow, QWidget#appRoot, QWidget#page, QDialog {{
    background-color: {BG};
}}
QLabel {{ background: transparent; }}

/* Barra laterale */
QFrame#sidebar {{ background-color: {SIDEBAR}; }}
QLabel#logo {{ color: white; font-size: 19px; font-weight: 800; padding: 6px 12px 18px 12px; }}
QPushButton#navButton {{
    background: transparent; color: #cbd5e1; border: none; border-radius: 10px;
    text-align: left; padding: 12px 14px; font-size: 15px; font-weight: 600;
}}
QPushButton#navButton:hover {{ background-color: {SIDEBAR_HOVER}; color: white; }}
QPushButton#navButton:checked {{
    background-color: {SIDEBAR_HOVER}; color: white; border-left: 3px solid {BLUE_SOFT};
}}
QLabel#navBadge {{
    background-color: {RED}; color: white; border-radius: 9px;
    padding: 1px 7px; font-size: 12px; font-weight: 700;
}}

/* Titoli */
QLabel#pageTitle {{ font-size: 26px; font-weight: 800; }}
QLabel#pageSubtitle, QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#cardTitle {{ font-size: 17px; font-weight: 800; }}
QLabel#cardHint {{ color: {TEXT_MUTED}; font-size: 13px; }}
QLabel#emptyState {{ color: {TEXT_MUTED}; font-size: 14px; padding: 18px; }}
QLabel#fieldLabel {{ color: #334155; font-weight: 600; }}

/* Card */
QFrame#card {{ background-color: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px; }}
QLabel#kpiLabel {{ color: #475569; font-weight: 600; }}
QLabel#kpiValue {{ font-size: 30px; font-weight: 800; }}
QLabel#kpiHint {{ color: {TEXT_MUTED}; font-size: 13px; }}

/* Pulsanti */
QPushButton {{
    background-color: white; color: {TEXT}; border: 1px solid {BORDER_STRONG};
    border-radius: 10px; padding: 10px 16px; font-weight: 700;
}}
QPushButton:hover {{ background-color: #f8fafc; }}
QPushButton:disabled {{ color: {TEXT_SOFT}; }}
QPushButton#primary {{ background-color: {BLUE}; color: white; border: none; }}
QPushButton#primary:hover {{ background-color: #1d4ed8; }}
QPushButton#success {{ background-color: {GREEN}; color: white; border: none; padding: 6px 12px; font-size: 13px; }}
QPushButton#success:hover {{ background-color: {GREEN_DARK}; }}
QPushButton#danger {{ background-color: white; color: {RED_DARK}; border: 1px solid #fecaca; }}
QPushButton#danger:hover {{ background-color: #fef2f2; }}
QPushButton#link {{ background: transparent; border: none; color: {BLUE}; padding: 4px; }}
QPushButton#link:hover {{ text-decoration: underline; }}

/* Filtri a "pillola" */
QPushButton#tab {{
    background-color: white; border: 1px solid {BORDER_STRONG}; border-radius: 17px;
    padding: 7px 16px; font-weight: 600;
}}
QPushButton#tab:checked {{ background-color: {TEXT}; color: white; border-color: {TEXT}; }}
QPushButton#tabDanger {{
    background-color: white; border: 1px solid {BORDER_STRONG}; border-radius: 17px;
    padding: 7px 16px; font-weight: 600; color: {RED_DARK};
}}
QPushButton#tabDanger:checked {{ background-color: {RED}; color: white; border-color: {RED}; }}

/* Campi */
QLineEdit, QComboBox, QDateEdit, QTextEdit, QTimeEdit {{
    background-color: white; border: 1px solid {BORDER_STRONG}; border-radius: 10px;
    padding: 8px 12px; min-height: 22px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus, QTimeEdit:focus {{
    border: 2px solid {BLUE_SOFT};
}}
QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: white; selection-background-color: #eff6ff; selection-color: {TEXT}; }}

/* Tabelle */
QTableWidget {{
    background-color: white; border: none; gridline-color: transparent;
    selection-background-color: #eff6ff; selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }}
QHeaderView::section {{
    background-color: white; color: {TEXT_MUTED}; font-size: 12px; font-weight: 700;
    padding: 8px; border: none; border-bottom: 1px solid {BORDER};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}

QListWidget {{ background: white; border: none; outline: none; }}
QListWidget::item {{ padding: 10px 8px; border-bottom: 1px solid #f1f5f9; }}
QListWidget::item:selected {{ background-color: #eff6ff; color: {TEXT}; }}

QCalendarWidget QWidget {{ alternate-background-color: white; }}
QCalendarWidget QToolButton {{ color: {TEXT}; font-weight: 700; background: transparent; padding: 6px; }}
QCalendarWidget QAbstractItemView {{ selection-background-color: {BLUE}; selection-color: white; }}
"""


def light_palette():
    """Palette chiara fissa: l'app resta leggibile anche se il Mac è in modalità scura."""
    from PySide6.QtGui import QColor, QPalette

    pal = QPalette()
    colori = {
        QPalette.ColorRole.Window: BG,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: SURFACE,
        QPalette.ColorRole.AlternateBase: "#f8fafc",
        QPalette.ColorRole.ToolTipBase: SURFACE,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: SURFACE,
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.Highlight: BLUE,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: TEXT_SOFT,
        QPalette.ColorRole.Link: BLUE,
    }
    for ruolo, colore in colori.items():
        pal.setColor(ruolo, QColor(colore))
    return pal
