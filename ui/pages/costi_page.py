"""Costi e guadagno per cantiere."""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QTableWidgetItem

from repositories.costi_repository import get_costi
from repositories.dashboard_repository import get_available_years, get_margine_per_cantiere
from ui import theme
from ui.dialogs import CostoDialog
from ui.widgets import Card, Page, PageHeader, button, label, make_table
from utils.validators import CATEGORIE_COSTO


class CostiPage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)
        self.righe: list[dict] = []

        header = PageHeader("Costi", "Doppio clic su una riga per modificarla o eliminarla")
        header.add_action(button("+ Nuovo costo", "primary", self._nuovo))
        self.root.addWidget(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Cerca descrizione, cliente o cantiere…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render)
        self.combo_anno = QComboBox()
        self.combo_anno.setMinimumWidth(150)
        self.combo_anno.currentIndexChanged.connect(self._render)
        self.combo_categoria = QComboBox()
        self.combo_categoria.setMinimumWidth(170)
        self.combo_categoria.addItem("Tutte le categorie", None)
        for c in CATEGORIE_COSTO:
            self.combo_categoria.addItem(c, c)
        self.combo_categoria.currentIndexChanged.connect(self._render)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.combo_categoria)
        filters.addWidget(self.combo_anno)
        self.root.addLayout(filters)

        body = QHBoxLayout()
        body.setSpacing(16)

        card = Card()
        self.table = make_table(["Data", "Descrizione", "Categoria", "Cliente / cantiere", "Importo"], stretch_cols=(1, 3))
        self.table.cellDoubleClicked.connect(lambda r, _c: self._apri(r))
        self.empty = label("Nessun costo registrato con questi filtri.", "emptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.body.addWidget(self.table, 1)
        card.body.addWidget(self.empty)
        foot = QHBoxLayout()
        self.lbl_count = label("", "fieldLabel")
        self.lbl_totale = label("", "fieldLabel")
        foot.addWidget(self.lbl_count)
        foot.addStretch()
        foot.addWidget(self.lbl_totale)
        card.body.addLayout(foot)
        body.addWidget(card, 3)

        self.card_margini = Card("Guadagno per cantiere", "")
        self.table_margini = make_table(["Cantiere", "Fatturato", "Costi", "Guadagno"], stretch_cols=(0,))
        self.empty_margini = label("Collega fatture e costi a un cantiere per vedere quanto rende.", "emptyState", wrap=True)
        self.card_margini.body.addWidget(self.table_margini, 1)
        self.card_margini.body.addWidget(self.empty_margini)
        body.addWidget(self.card_margini, 2)

        self.root.addLayout(body, 1)

    def refresh(self) -> None:
        corrente = self.combo_anno.currentData() if self.combo_anno.count() else date.today().strftime("%Y")
        self.combo_anno.blockSignals(True)
        self.combo_anno.clear()
        self.combo_anno.addItem("Tutti gli anni", None)
        for a in get_available_years():
            self.combo_anno.addItem(a, a)
        idx = self.combo_anno.findData(corrente)
        self.combo_anno.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_anno.blockSignals(False)
        self._render()

    def _render(self, *_args) -> None:
        anno = self.combo_anno.currentData()
        righe = get_costi(anno=anno, categoria=self.combo_categoria.currentData())
        testo = self.search.text().strip().lower()
        if testo:
            righe = [c for c in righe if any(
                testo in str(v).lower() for v in (c.get("descrizione"), c.get("cliente_nome"), c.get("cantiere_nome"), c.get("note")) if v
            )]
        self.righe = righe

        self.table.setVisible(bool(righe))
        self.empty.setVisible(not righe)
        self.table.setRowCount(len(righe))
        for r, c in enumerate(righe):
            self.table.setItem(r, 0, QTableWidgetItem(theme.fmt_data(c["data"])))
            desc = QTableWidgetItem(c["descrizione"])
            if c.get("note"):
                desc.setToolTip(f"Note: {c['note']}")
            self.table.setItem(r, 1, desc)
            self.table.setItem(r, 2, QTableWidgetItem(c.get("categoria") or "—"))
            dove = " · ".join(x for x in (c.get("cliente_nome"), c.get("cantiere_nome")) if x) or "Spesa generale"
            self.table.setItem(r, 3, QTableWidgetItem(dove))
            imp = QTableWidgetItem(theme.fmt_euro(c["importo"]))
            font = imp.font()
            font.setBold(True)
            imp.setFont(font)
            imp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 4, imp)

        self.lbl_count.setText(f"{len(righe)} cost{'o' if len(righe) == 1 else 'i'}")
        self.lbl_totale.setText(f"Totale: {theme.fmt_euro(sum(c['importo'] for c in righe))}")

        self._render_margini(anno)

    def _render_margini(self, anno: str | None) -> None:
        margini = get_margine_per_cantiere(anno)
        self.card_margini.hint_label.setText(f"anno {anno}" if anno else "tutti gli anni")
        self.table_margini.setVisible(bool(margini))
        self.empty_margini.setVisible(not margini)
        self.table_margini.setRowCount(len(margini))
        for r, m in enumerate(margini):
            nome = QTableWidgetItem(m["cantiere_nome"])
            nome.setToolTip(m["cliente_nome"])
            self.table_margini.setItem(r, 0, nome)
            for col, key in ((1, "ricavi"), (2, "costi")):
                it = QTableWidgetItem(theme.fmt_euro(m[key], 0))
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_margini.setItem(r, col, it)
            g = QTableWidgetItem(theme.fmt_euro(m["margine"], 0))
            g.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            font = g.font()
            font.setBold(True)
            g.setFont(font)
            g.setForeground(QBrush(QColor(theme.GREEN_DARK if m["margine"] >= 0 else theme.RED_DARK)))
            self.table_margini.setItem(r, 3, g)

    def _apri(self, row: int) -> None:
        if 0 <= row < len(self.righe) and CostoDialog(self, costo=self.righe[row]).exec():
            self.notify_changed()

    def _nuovo(self) -> None:
        if CostoDialog(self).exec():
            self.notify_changed()
