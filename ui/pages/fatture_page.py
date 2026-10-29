"""Elenco fatture con filtri semplici."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
)

from repositories.dashboard_repository import get_available_years
from repositories.fatture_repository import get_fattura_by_id, get_fatture
from repositories.group_repository import get_all_groups
from services.fatture_service import update_fattura_status_service
from ui import theme
from ui.dialogs import FatturaDialog
from ui.widgets import Card, Page, PageHeader, Pill, button, errore, label, make_table
from utils.pdf_export import export_fatture_to_pdf

TABS = [
    ("tutte", "Tutte", "tab"),
    ("aperte", "Da incassare", "tab"),
    ("scadute", "Scadute", "tabDanger"),
    ("pagate", "Pagate", "tab"),
]


class FatturePage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)
        self.tab = "tutte"
        self.righe: list[dict] = []

        header = PageHeader("Fatture", "Doppio clic su una riga per aprirla e modificarla")
        header.add_action(button("Esporta PDF", None, self._esporta_pdf))
        header.add_action(button("+ Nuova fattura", "primary", self._nuova))
        self.root.addWidget(header)

        # Filtri a pillola
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(8)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_buttons = {}
        for key, testo, stile in TABS:
            btn = button(testo, stile)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self.set_tab(k))
            self.tab_group.addButton(btn)
            self.tab_buttons[key] = (btn, testo)
            tabs_row.addWidget(btn)
        tabs_row.addStretch()
        self.root.addLayout(tabs_row)

        # Ricerca e filtri
        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Cerca cliente, cantiere, numero fattura o nota…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render)
        self.combo_gruppo = QComboBox()
        self.combo_gruppo.setMinimumWidth(170)
        self.combo_gruppo.currentIndexChanged.connect(self._render)
        self.combo_anno = QComboBox()
        self.combo_anno.setMinimumWidth(150)
        self.combo_anno.currentIndexChanged.connect(self._render)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.combo_gruppo)
        filters.addWidget(self.combo_anno)
        self.root.addLayout(filters)

        # Tabella
        card = Card()
        self.table = make_table(["N°", "Data", "Cliente", "Cantiere", "Importo", "Scadenza", "Stato"], stretch_cols=(2, 3))
        self.table.cellDoubleClicked.connect(lambda r, _c: self._apri(r))
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        self.empty = label("Nessuna fattura trovata con questi filtri.", "emptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.body.addWidget(self.table, 1)
        card.body.addWidget(self.empty)
        foot = QHBoxLayout()
        self.lbl_count = label("", "fieldLabel")
        self.lbl_totali = label("", "fieldLabel")
        foot.addWidget(self.lbl_count)
        foot.addStretch()
        foot.addWidget(self.lbl_totali)
        card.body.addLayout(foot)
        self.root.addWidget(card, 1)

        self.tab_buttons["tutte"][0].setChecked(True)

    # --- dati -------------------------------------------------------------------------------
    def refresh(self) -> None:
        self._reload_combo(self.combo_gruppo, "Tutti i gruppi", [(g["nome"], g["id"]) for g in get_all_groups()])
        anni = get_available_years()
        self._reload_combo(self.combo_anno, "Tutti gli anni", [(a, a) for a in anni])
        self._render()

    @staticmethod
    def _reload_combo(combo: QComboBox, tutti: str, voci: list[tuple[str, object]]) -> None:
        corrente = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tutti, None)
        for testo, valore in voci:
            combo.addItem(testo, valore)
        idx = combo.findData(corrente)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def set_tab(self, key: str) -> None:
        self.tab = key
        self.tab_buttons[key][0].setChecked(True)
        self._render()

    def _filtra(self) -> tuple[list[dict], dict]:
        tutte = get_fatture(group_id=self.combo_gruppo.currentData())

        anno = self.combo_anno.currentData()
        if anno:
            tutte = [f for f in tutte if (f.get("data_inserimento") or "").startswith(anno)]

        testo = self.search.text().strip().lower()
        if testo:
            def match(f):
                campi = (f.get("cliente_nome"), f.get("cantiere_nome"), f.get("numero_fattura"),
                         f.get("note"), f.get("gruppo_nome"))
                return any(testo in str(c).lower() for c in campi if c)
            tutte = [f for f in tutte if match(f)]

        gruppi = {
            "tutte": tutte,
            "aperte": [f for f in tutte if f["stato"] != "Pagato"],
            "scadute": [f for f in tutte if theme.da_sollecitare(f)],
            "pagate": [f for f in tutte if f["stato"] == "Pagato"],
        }
        return gruppi[self.tab], {k: len(v) for k, v in gruppi.items()}

    def _render(self, *_args) -> None:
        righe, conteggi = self._filtra()
        self.righe = righe

        for key, (btn, testo) in self.tab_buttons.items():
            btn.setText(f"{testo} ({conteggi[key]})")

        self.table.setVisible(bool(righe))
        self.empty.setVisible(not righe)
        self.table.setRowCount(len(righe))
        bold = None
        for r, f in enumerate(righe):
            self.table.setItem(r, 0, QTableWidgetItem(f.get("numero_fattura") or "—"))
            self.table.setItem(r, 1, QTableWidgetItem(theme.fmt_data(f.get("data_inserimento"))))
            cliente = QTableWidgetItem(f.get("cliente_nome") or "")
            if bold is None:
                bold = cliente.font()
                bold.setBold(True)
            cliente.setFont(bold)
            if f.get("note"):
                cliente.setToolTip(f"Note: {f['note']}")
            self.table.setItem(r, 2, cliente)
            self.table.setItem(r, 3, QTableWidgetItem(f.get("cantiere_nome") or "—"))
            imp = QTableWidgetItem(theme.fmt_euro(f["importo"]))
            imp.setFont(bold)
            imp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 4, imp)
            scad = QTableWidgetItem(theme.fmt_data(f.get("data_scadenza")) if f["stato"] != "Pagato" else "—")
            if theme.is_scaduta(f):
                scad.setForeground(QBrush(QColor(theme.RED_DARK)))
                scad.setFont(bold)
            self.table.setItem(r, 5, scad)
            testo, colore = theme.stato_fattura(f)
            self.table.setCellWidget(r, 6, Pill(testo, colore))

        totale = sum(f["importo"] for f in righe)
        aperto = sum(f["importo"] for f in righe if f["stato"] != "Pagato")
        self.lbl_count.setText(f"{len(righe)} fattur{'a' if len(righe) == 1 else 'e'}")
        self.lbl_totali.setText(f"Totale: {theme.fmt_euro(totale)}   ·   Da incassare: {theme.fmt_euro(aperto)}")

    # --- azioni ------------------------------------------------------------------------------
    def _apri(self, row: int) -> None:
        if 0 <= row < len(self.righe) and self.app_window:
            self.app_window.modifica_fattura(self.righe[row]["id"])

    def _menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if not (0 <= row < len(self.righe)):
            return
        f = self.righe[row]
        menu = QMenu(self)
        menu.addAction("Apri / modifica").triggered.connect(lambda: self._apri(row))
        if f["stato"] != "Pagato":
            menu.addAction("✓ Segna come pagata oggi").triggered.connect(lambda: self._segna_pagata(f["id"]))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _segna_pagata(self, fattura_id: int) -> None:
        try:
            update_fattura_status_service(fattura_id, "Pagato")
        except Exception as exc:
            errore(self, exc)
        QTimer.singleShot(0, self.notify_changed)

    def _nuova(self) -> None:
        if FatturaDialog(self).exec():
            self.notify_changed()

    def _esporta_pdf(self) -> None:
        if not self.righe:
            QMessageBox.information(self, "Esporta PDF", "Non ci sono fatture da esportare con questi filtri.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva PDF", "fatture.pdf", "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_fatture_to_pdf(
                filepath=path,
                fatture=self.righe,
                filtro_gruppo=self.combo_gruppo.currentText(),
                filtro_cliente=self.search.text().strip() or "Tutti",
                filtro_stato=self.tab_buttons[self.tab][1],
            )
            QMessageBox.information(self, "Esporta PDF", f"PDF salvato:\n{path}")
        except Exception as exc:
            errore(self, exc)


def apri_fattura(parent, fattura_id: int) -> bool:
    """Apre la finestra di modifica di una fattura. True se qualcosa è cambiato."""
    fattura = get_fattura_by_id(fattura_id)
    if not fattura:
        errore(parent, "Fattura non trovata.")
        return False
    return bool(FatturaDialog(parent, fattura=fattura).exec())
