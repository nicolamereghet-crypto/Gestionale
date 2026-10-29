"""Storico: tutto quello che è stato fatto, dal più recente."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QTableWidgetItem

from repositories.storico_repository import get_storico
from ui.widgets import Card, Page, PageHeader, Pill, label, make_table

AZIONI = {
    "CREAZIONE_FATTURA": ("Nuova fattura", "blu"),
    "MODIFICA_FATTURA": ("Fattura modificata", "grigio"),
    "MODIFICA_STATO": ("Cambio stato", "arancio"),
    "ELIMINAZIONE_FATTURA": ("Fattura eliminata", "rosso"),
    "CREAZIONE_COSTO": ("Nuovo costo", "blu"),
    "MODIFICA_COSTO": ("Costo modificato", "grigio"),
    "ELIMINAZIONE_COSTO": ("Costo eliminato", "rosso"),
    "CREAZIONE_CLIENTE": ("Nuovo cliente", "blu"),
    "MODIFICA_CLIENTE": ("Cliente modificato", "grigio"),
    "ELIMINAZIONE_CLIENTE": ("Cliente eliminato", "rosso"),
    "CREAZIONE_CANTIERE": ("Nuovo cantiere", "blu"),
    "MODIFICA_CANTIERE": ("Cantiere modificato", "grigio"),
    "ELIMINAZIONE_CANTIERE": ("Cantiere eliminato", "rosso"),
    "MODIFICA_GRUPPO": ("Gruppo modificato", "grigio"),
    "ELIMINAZIONE_GRUPPO": ("Gruppo eliminato", "rosso"),
}

MAX_RIGHE = 500


def _fmt_quando(valore: str) -> str:
    # 'YYYY-MM-DD HH:MM:SS' oppure solo 'YYYY-MM-DD' (registrazioni vecchie)
    data, _, ora = (valore or "").partition(" ")
    parti = data.split("-")
    if len(parti) == 3:
        data = f"{parti[2]}/{parti[1]}/{parti[0]}"
    return f"{data}  {ora[:5]}".strip()


class StoricoPage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)
        self.root.addWidget(PageHeader("Storico", "Tutte le operazioni fatte nel gestionale, dalla più recente"))

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Cerca nei dettagli…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(200)
        self.combo.addItem("Tutte le operazioni", "Tutte")
        for key, (testo, _c) in AZIONI.items():
            self.combo.addItem(testo, key)
        self.combo.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.combo)
        self.root.addLayout(filters)

        card = Card()
        self.table = make_table(["Quando", "Operazione", "Dettagli"], stretch_cols=(2,))
        self.empty = label("Nessuna operazione trovata.", "emptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_count = label("", "muted")
        card.body.addWidget(self.table, 1)
        card.body.addWidget(self.empty)
        card.body.addWidget(self.lbl_count)
        self.root.addWidget(card, 1)

    def refresh(self, *_args) -> None:
        righe = get_storico(search_text=self.search.text(), azione_filter=self.combo.currentData() or "Tutte")
        totale = len(righe)
        righe = righe[:MAX_RIGHE]
        self.table.setVisible(bool(righe))
        self.empty.setVisible(not righe)
        self.table.setRowCount(len(righe))
        for r, s in enumerate(righe):
            self.table.setItem(r, 0, QTableWidgetItem(_fmt_quando(s["data_evento"])))
            testo, colore = AZIONI.get(s["azione"], (s["azione"], "grigio"))
            self.table.setCellWidget(r, 1, Pill(testo, colore))
            det = QTableWidgetItem(s.get("dettagli") or "")
            det.setToolTip(s.get("dettagli") or "")
            self.table.setItem(r, 2, det)
        extra = f" (mostrate le ultime {MAX_RIGHE})" if totale > MAX_RIGHE else ""
        self.lbl_count.setText(f"{totale} operazioni{extra}")
