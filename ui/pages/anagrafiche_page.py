"""Clienti e cantieri."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QTableWidgetItem, QVBoxLayout

from repositories.cantieri_repository import get_cantieri_by_cliente
from repositories.clienti_repository import get_all_clienti
from repositories.fatture_repository import get_fatture
from repositories.group_repository import get_all_groups
from ui import theme
from ui.dialogs import CantiereDialog, ClienteDialog, GruppiDialog
from ui.widgets import Card, Page, PageHeader, button, label, make_table


class AnagrafichePage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)
        self.clienti: list[dict] = []
        self.cantieri: list[dict] = []
        self.cliente_sel: dict | None = None

        header = PageHeader("Clienti e cantieri", "Seleziona un cliente per vedere i suoi cantieri e la sua situazione")
        header.add_action(button("Gruppi…", None, self._gruppi))
        header.add_action(button("+ Nuovo cliente", "primary", self._nuovo_cliente))
        self.root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        # Sinistra: elenco clienti
        left = Card()
        filtri = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Cerca cliente…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render_lista)
        self.combo_gruppo = QComboBox()
        self.combo_gruppo.currentIndexChanged.connect(self._render_lista)
        filtri.addWidget(self.search, 1)
        filtri.addWidget(self.combo_gruppo)
        left.body.addLayout(filtri)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._on_select)
        self.lista.itemDoubleClicked.connect(lambda *_: self._modifica_cliente())
        left.body.addWidget(self.lista, 1)
        self.lbl_count = label("", "muted")
        left.body.addWidget(self.lbl_count)
        body.addWidget(left, 2)

        # Destra: dettaglio
        right = QVBoxLayout()
        right.setSpacing(16)

        self.card_cliente = Card()
        head = QHBoxLayout()
        self.lbl_nome = label("", "pageTitle")
        head.addWidget(self.lbl_nome, 1)
        self.btn_modifica = button("Modifica cliente", None, self._modifica_cliente)
        head.addWidget(self.btn_modifica)
        self.card_cliente.body.addLayout(head)
        self.lbl_info = label("", "muted", wrap=True)
        self.card_cliente.body.addWidget(self.lbl_info)
        self.lbl_numeri = label("", "fieldLabel", wrap=True)
        self.card_cliente.body.addWidget(self.lbl_numeri)
        right.addWidget(self.card_cliente)

        self.card_cantieri = Card("Cantieri", "doppio clic per modificare")
        self.table = make_table(["Cantiere", "Località", "Indirizzo"], stretch_cols=(0, 2))
        self.table.cellDoubleClicked.connect(lambda r, _c: self._modifica_cantiere(r))
        self.empty_cantieri = label("Questo cliente non ha ancora cantieri.", "emptyState")
        self.card_cantieri.body.addWidget(self.table, 1)
        self.card_cantieri.body.addWidget(self.empty_cantieri)
        self.card_cantieri.body.addWidget(button("+ Nuovo cantiere", None, self._nuovo_cantiere), 0, Qt.AlignmentFlag.AlignLeft)
        right.addWidget(self.card_cantieri, 1)

        self.empty_dettaglio = label("Seleziona un cliente dall'elenco a sinistra.", "emptyState")
        self.empty_dettaglio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.empty_dettaglio, 1)

        body.addLayout(right, 3)
        self.root.addLayout(body, 1)

    # --- dati -------------------------------------------------------------------------------
    def refresh(self, select_id: int | None = None) -> None:
        if select_id is None and self.cliente_sel:
            select_id = self.cliente_sel["id"]
        corrente = self.combo_gruppo.currentData()
        self.combo_gruppo.blockSignals(True)
        self.combo_gruppo.clear()
        self.combo_gruppo.addItem("Tutti i gruppi", None)
        for g in get_all_groups():
            self.combo_gruppo.addItem(g["nome"], g["id"])
        idx = self.combo_gruppo.findData(corrente)
        self.combo_gruppo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_gruppo.blockSignals(False)
        self._render_lista(select_id=select_id)

    def _render_lista(self, *_args, select_id: int | None = None) -> None:
        if select_id is None and self.cliente_sel:
            select_id = self.cliente_sel["id"]
        clienti = get_all_clienti(group_id=self.combo_gruppo.currentData())
        testo = self.search.text().strip().lower()
        if testo:
            clienti = [c for c in clienti if testo in c["nome"].lower()]
        self.clienti = clienti

        self.lista.blockSignals(True)
        self.lista.clear()
        riga_sel = -1
        for i, c in enumerate(clienti):
            testo_item = c["nome"] + (f"\n{c['gruppo_nome']}" if c.get("gruppo_nome") else "")
            item = QListWidgetItem(testo_item)
            self.lista.addItem(item)
            if c["id"] == select_id:
                riga_sel = i
        self.lista.blockSignals(False)
        self.lbl_count.setText(f"{len(clienti)} client{'e' if len(clienti) == 1 else 'i'}")

        if riga_sel < 0 and clienti:
            riga_sel = 0
        self.lista.setCurrentRow(riga_sel)
        self._on_select(riga_sel)

    def _on_select(self, row: int) -> None:
        self.cliente_sel = self.clienti[row] if 0 <= row < len(self.clienti) else None
        has = self.cliente_sel is not None
        self.card_cliente.setVisible(has)
        self.card_cantieri.setVisible(has)
        self.empty_dettaglio.setVisible(not has)
        if not has:
            return

        c = self.cliente_sel
        self.lbl_nome.setText(c["nome"])
        info = [f"Gruppo: {c.get('gruppo_nome') or 'nessuno'}"]
        if c.get("telefono"):
            info.append(f"Tel. {c['telefono']}")
        if c.get("email"):
            info.append(c["email"])
        self.lbl_info.setText("   ·   ".join(info) + (f"\n{c['note']}" if c.get("note") else ""))

        fatture = get_fatture(cliente_id=c["id"])
        totale = sum(f["importo"] for f in fatture)
        aperto = sum(f["importo"] for f in fatture if f["stato"] != "Pagato")
        scadute = [f for f in fatture if theme.is_scaduta(f)]
        numeri = f"{len(fatture)} fatture per {theme.fmt_euro(totale)}   ·   da incassare {theme.fmt_euro(aperto)}"
        if scadute:
            numeri += f"   ·   ⚠️ {len(scadute)} scadut{'a' if len(scadute) == 1 else 'e'}"
        self.lbl_numeri.setText(numeri)

        self.cantieri = get_cantieri_by_cliente(c["id"])
        self.table.setVisible(bool(self.cantieri))
        self.empty_cantieri.setVisible(not self.cantieri)
        self.table.setRowCount(len(self.cantieri))
        for r, ca in enumerate(self.cantieri):
            nome = QTableWidgetItem(ca["nome"])
            if ca.get("note"):
                nome.setToolTip(ca["note"])
            self.table.setItem(r, 0, nome)
            self.table.setItem(r, 1, QTableWidgetItem(ca.get("localita") or "—"))
            self.table.setItem(r, 2, QTableWidgetItem(ca.get("indirizzo") or "—"))

    # --- azioni ------------------------------------------------------------------------------
    def _nuovo_cliente(self) -> None:
        dlg = ClienteDialog(self)
        if dlg.exec():
            self.search.clear()
            self.refresh(select_id=dlg.saved_id)
            self.notify_changed()

    def _modifica_cliente(self) -> None:
        if not self.cliente_sel:
            return
        if ClienteDialog(self, cliente=self.cliente_sel).exec():
            self.notify_changed()

    def _nuovo_cantiere(self) -> None:
        if not self.cliente_sel:
            return
        if CantiereDialog(self, cliente_id=self.cliente_sel["id"]).exec():
            self.notify_changed()

    def _modifica_cantiere(self, row: int) -> None:
        if 0 <= row < len(self.cantieri) and CantiereDialog(self, cantiere=self.cantieri[row]).exec():
            self.notify_changed()

    def _gruppi(self) -> None:
        dlg = GruppiDialog(self)
        dlg.exec()
        if dlg.changed:
            self.notify_changed()
