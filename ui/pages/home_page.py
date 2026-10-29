"""Home: la situazione di oggi in un colpo d'occhio."""
from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from repositories.dashboard_repository import get_crediti_aperti, get_incassi_attesi, get_riepilogo_anno
from repositories.tasks_repository import get_tasks_by_date, toggle_task_done
from services.fatture_service import update_fattura_status_service
from ui import theme
from ui.dialogs import CostoDialog, FatturaDialog, TaskDialog
from ui.widgets import BarChart, Card, KpiCard, Page, PageHeader, Pill, button, clear_layout, errore, label, make_table

MAX_SOLLECITI = 6


class HomePage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)

        self.header = PageHeader(theme.saluto(), "")
        self.header.add_action(button("+ Nuovo costo", None, self._nuovo_costo))
        self.header.add_action(button("+ Nuova fattura", "primary", self._nuova_fattura))
        self.root.addWidget(self.header)

        # Riga dei 4 numeri
        kpis = QGridLayout()
        kpis.setSpacing(16)
        self.kpi_aperto = KpiCard("Ti devono ancora", "arancio")
        self.kpi_scaduto = KpiCard("Di cui da sollecitare", "rosso")
        self.kpi_incassato = KpiCard("Incassato quest'anno", "verde")
        self.kpi_guadagno = KpiCard("Guadagno quest'anno", "blu")
        for i, card in enumerate([self.kpi_aperto, self.kpi_scaduto, self.kpi_incassato, self.kpi_guadagno]):
            kpis.addWidget(card, 0, i)
        self.root.addLayout(kpis)

        # Colonna sinistra: solleciti + grafico. Colonna destra: attività di oggi.
        body = QHBoxLayout()
        body.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)

        self.card_solleciti = Card("⚠️  Da sollecitare", "fatture scadute o insolute, la più vecchia per prima")
        self.table = make_table(["Cliente", "Cantiere", "Fattura", "Importo", "Ritardo", ""], stretch_cols=(0, 1))
        self.table.cellDoubleClicked.connect(self._apri_fattura)
        self.empty_solleciti = label("Nessuna fattura scaduta. Ottimo! 🎉", "emptyState")
        self.link_tutte = button("Vedi tutte le fatture scadute →", "link",
                                 lambda: self.app_window and self.app_window.show_fatture("scadute"))
        self.card_solleciti.body.addWidget(self.table)
        self.card_solleciti.body.addWidget(self.empty_solleciti)
        self.card_solleciti.body.addWidget(self.link_tutte, 0, Qt.AlignmentFlag.AlignRight)
        left.addWidget(self.card_solleciti)

        self.card_grafico = Card("Quando entrano i soldi", "fatture non pagate, per mese di scadenza")
        self.chart = BarChart()
        self.card_grafico.body.addWidget(self.chart, 1)
        left.addWidget(self.card_grafico, 1)

        self.card_task = Card("✅  Da fare oggi", "")
        self.task_list = QVBoxLayout()
        self.task_list.setSpacing(0)
        self.card_task.body.addLayout(self.task_list)
        self.card_task.body.addWidget(button("+ Aggiungi attività", None, self._nuova_task), 0, Qt.AlignmentFlag.AlignLeft)
        self.card_task.body.addStretch()

        body.addLayout(left, 16)
        body.addWidget(self.card_task, 10)
        self.root.addLayout(body, 1)

        self._fatture_righe: list[dict] = []

    # --- aggiornamento --------------------------------------------------------------
    def refresh(self) -> None:
        self.header.title_label.setText(f"{theme.saluto()} 👋")
        self.header.subtitle_label.setText(f"{theme.oggi_esteso()} · ecco la situazione di oggi")

        crediti = get_crediti_aperti()
        scadute = [c for c in crediti if c["da_sollecitare"]]
        tot_aperto = sum(c["importo"] for c in crediti)
        tot_scaduto = sum(c["importo"] for c in scadute)
        anno = get_riepilogo_anno()

        self.kpi_aperto.set_values(theme.fmt_euro(tot_aperto, 0), self._n(len(crediti), "fattura non pagata", "fatture non pagate"))
        self.kpi_scaduto.set_values(
            theme.fmt_euro(tot_scaduto, 0),
            self._n(len(scadute), "fattura scaduta o insoluta", "fatture scadute o insolute") if scadute else "nessuna fattura scaduta",
        )
        self.kpi_incassato.set_values(theme.fmt_euro(anno["incassato"], 0),
                                      self._n(anno["numero_pagate"], "fattura pagata", "fatture pagate"),
                                      title=f"Incassato nel {anno['anno']}")
        self.kpi_guadagno.set_values(theme.fmt_euro(anno["guadagno"], 0),
                                     f"fatturato {theme.fmt_euro(anno['fatturato'], 0)} − costi {theme.fmt_euro(anno['costi'], 0)}",
                                     title=f"Guadagno nel {anno['anno']}")

        self._fill_solleciti(scadute)
        self._fill_chart()
        self._fill_tasks()

    @staticmethod
    def _n(n: int, singolare: str, plurale: str) -> str:
        return f"{n} {singolare if n == 1 else plurale}"

    def _fill_solleciti(self, scadute: list[dict]) -> None:
        # le più vecchie per prime
        scadute = sorted(scadute, key=lambda c: c["data_scadenza"] or c["data_inserimento"])
        righe = scadute[:MAX_SOLLECITI]
        self._fatture_righe = righe

        self.table.setVisible(bool(righe))
        self.empty_solleciti.setVisible(not righe)
        self.link_tutte.setVisible(len(scadute) > MAX_SOLLECITI)
        self.link_tutte.setText(f"Vedi tutte le {len(scadute)} fatture scadute →")

        self.table.setRowCount(len(righe))
        for r, f in enumerate(righe):
            cliente = QTableWidgetItem(f["cliente_nome"] or "")
            font = cliente.font()
            font.setBold(True)
            cliente.setFont(font)
            self.table.setItem(r, 0, cliente)
            self.table.setItem(r, 1, QTableWidgetItem(f.get("cantiere_nome") or "—"))
            self.table.setItem(r, 2, QTableWidgetItem(f.get("numero_fattura") or "—"))
            imp = QTableWidgetItem(theme.fmt_euro(f["importo"]))
            imp.setFont(font)
            imp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 3, imp)
            giorni = f["giorni_ritardo"]
            if f["scaduta"]:
                testo_pill = "oggi" if giorni == 0 else f"{giorni} giorn{'o' if giorni == 1 else 'i'}"
            else:
                testo_pill = "insoluta"
            self.table.setCellWidget(r, 4, Pill(testo_pill, "rosso"))

            wrap = QWidget()
            lay = QHBoxLayout(wrap)
            lay.setContentsMargins(4, 4, 4, 4)
            btn = button("✓ Pagata", "success", lambda _=False, fid=f["id"]: self._segna_pagata(fid))
            btn.setToolTip("Segna la fattura come pagata oggi")
            lay.addWidget(btn)
            self.table.setCellWidget(r, 5, wrap)

        # altezza della tabella adattata alle righe (niente spazio vuoto)
        h = self.table.horizontalHeader().height() + sum(self.table.rowHeight(i) for i in range(len(righe))) + 4
        self.table.setFixedHeight(h)

    def _fill_chart(self) -> None:
        dati = []
        for riga in get_incassi_attesi(mesi=5):
            if riga["chiave"] == "oltre" and not riga["importo"]:
                continue
            if riga["chiave"] == "senza_scadenza" and not riga["importo"]:
                continue
            colore = theme.RED if riga["chiave"] == "scadute" else theme.GREY_BAR if riga["chiave"] in ("senza_scadenza", "oltre") else theme.BLUE_SOFT
            etichetta = riga["etichetta"] if riga["chiave"] in ("scadute", "senza_scadenza", "oltre") else riga["etichetta"].split()[0]
            dati.append((etichetta, riga["importo"], colore))
        self.chart.set_data(dati)

    def _fill_tasks(self) -> None:
        clear_layout(self.task_list)
        tasks = get_tasks_by_date(date.today().isoformat())
        fatte = sum(1 for t in tasks if t["done"])
        self.card_task.hint_label.setText(f"{fatte} su {len(tasks)} fatte" if tasks else "")
        if not tasks:
            self.task_list.addWidget(label("Niente in programma per oggi.", "emptyState"))
            return
        for t in tasks:
            self.task_list.addWidget(self._task_row(t))

    def _task_row(self, t: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet(f"QWidget#taskRow {{ border-bottom: 1px solid #f1f5f9; }}")
        row.setObjectName("taskRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(10)

        chk = QCheckBox()
        chk.setChecked(bool(t["done"]))
        chk.toggled.connect(lambda checked, tid=t["id"]: self._toggle_task(tid, checked))
        ora = QLabel(t.get("orario") or "—")
        ora.setFixedWidth(44)
        ora.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        titolo = QLabel(t["titolo"])
        titolo.setWordWrap(True)
        if t["done"]:
            titolo.setStyleSheet(f"color: {theme.TEXT_SOFT}; text-decoration: line-through;")
        edit = button("Modifica", "link", lambda _=False, task=t: self._modifica_task(task))

        lay.addWidget(chk)
        lay.addWidget(ora)
        lay.addWidget(titolo, 1)
        lay.addWidget(edit)
        return row

    # --- azioni ----------------------------------------------------------------------------
    def _segna_pagata(self, fattura_id: int) -> None:
        try:
            update_fattura_status_service(fattura_id, "Pagato")
        except Exception as exc:
            errore(self, exc)
        # aggiornamento dopo che il clic è terminato (il pulsante viene ricreato)
        QTimer.singleShot(0, self.notify_changed)

    def _apri_fattura(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._fatture_righe) and self.app_window:
            self.app_window.modifica_fattura(self._fatture_righe[row]["id"])

    def _toggle_task(self, task_id: int, done: bool) -> None:
        toggle_task_done(task_id, done)
        QTimer.singleShot(0, self.notify_changed)

    def _modifica_task(self, task: dict) -> None:
        if TaskDialog(self, task=task).exec():
            self.notify_changed()

    def _nuova_task(self) -> None:
        if TaskDialog(self).exec():
            self.notify_changed()

    def _nuova_fattura(self) -> None:
        if FatturaDialog(self).exec():
            self.notify_changed()

    def _nuovo_costo(self) -> None:
        if CostoDialog(self).exec():
            self.notify_changed()
