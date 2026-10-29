"""Finestra principale: menu a sinistra e una schermata alla volta a destra."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from repositories.dashboard_repository import get_crediti_aperti
from ui.pages.anagrafiche_page import AnagrafichePage
from ui.pages.attivita_page import AttivitaPage
from ui.pages.costi_page import CostiPage
from ui.pages.fatture_page import FatturePage, apri_fattura
from ui.pages.home_page import HomePage
from ui.pages.storico_page import StoricoPage
from ui.widgets import label


class NavButton(QPushButton):
    """Voce del menu laterale, con un contatore rosso opzionale a destra."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 12, 0)
        lay.addStretch()
        self.badge = QLabel("")
        self.badge.setObjectName("navBadge")
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.badge.setVisible(False)
        lay.addWidget(self.badge)

    def set_badge(self, n: int) -> None:
        self.badge.setText(str(n))
        self.badge.setVisible(n > 0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestionale")
        self.resize(1400, 880)
        self.setMinimumSize(1100, 700)

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Schermate
        self.stack = QStackedWidget()
        self.pages = {
            "home": HomePage(self),
            "fatture": FatturePage(self),
            "costi": CostiPage(self),
            "clienti": AnagrafichePage(self),
            "attivita": AttivitaPage(self),
            "storico": StoricoPage(self),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        self._da_aggiornare: set[str] = set(self.pages)

        # Menu laterale
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 22, 14, 22)
        side.setSpacing(6)
        side.addWidget(label("Gestionale", "logo"))

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav: dict[str, NavButton] = {}
        voci = [
            ("home", "🏠   Home"),
            ("fatture", "📄   Fatture"),
            ("costi", "💸   Costi"),
            ("clienti", "👥   Clienti e cantieri"),
            ("attivita", "✅   Attività"),
        ]
        for key, testo in voci:
            side.addWidget(self._nav_button(key, testo))
        side.addStretch()
        side.addWidget(self._nav_button("storico", "🕘   Storico"))

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)

        # Scorciatoie da tastiera: Cmd/Ctrl+1..6 per cambiare schermata
        for i, key in enumerate(["home", "fatture", "costi", "clienti", "attivita", "storico"], start=1):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, activated=lambda k=key: self.show_page(k))

        self.show_page("home")

    def _nav_button(self, key: str, testo: str) -> NavButton:
        btn = NavButton(testo)
        btn.clicked.connect(lambda _=False, k=key: self.show_page(k))
        self.nav_group.addButton(btn)
        self.nav[key] = btn
        return btn

    # --- navigazione --------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        page = self.pages[key]
        self.nav[key].setChecked(True)
        if key in self._da_aggiornare:
            page.refresh()
            self._da_aggiornare.discard(key)
        self.stack.setCurrentWidget(page)
        self._corrente = key
        self._update_badges()

    def show_fatture(self, tab: str = "tutte") -> None:
        self.show_page("fatture")
        self.pages["fatture"].set_tab(tab)

    def current_key(self) -> str:
        return getattr(self, "_corrente", "home")

    # --- aggiornamenti ------------------------------------------------------------------
    def data_changed(self) -> None:
        """Chiamato da qualunque schermata dopo una modifica ai dati."""
        corrente = self.current_key()
        self._da_aggiornare = set(self.pages) - {corrente}
        self.pages[corrente].refresh()
        self._update_badges()

    def _update_badges(self) -> None:
        n = sum(1 for c in get_crediti_aperti() if c["da_sollecitare"])
        self.nav["fatture"].set_badge(n)
        self.nav["fatture"].setToolTip(f"{n} fatture da sollecitare" if n else "")

    # --- azioni condivise -----------------------------------------------------------------
    def modifica_fattura(self, fattura_id: int) -> None:
        if apri_fattura(self, fattura_id):
            self.data_changed()
