"""Finestre di inserimento e modifica.

Ogni finestra salva da sola (chiamando i service) e si chiude solo se il
salvataggio è andato a buon fine: chi la apre deve solo aggiornare la vista
quando exec() restituisce True.
"""
import re
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from repositories.cantieri_repository import get_cantieri_by_cliente
from repositories.clienti_repository import get_all_clienti
from repositories.group_repository import get_all_groups
from repositories.tasks_repository import create_task, delete_task, update_task
from services.anagrafiche_service import (
    create_cantiere_service,
    create_cliente_service,
    create_group_service,
    delete_cantiere_service,
    delete_cliente_service,
    delete_group_service,
    rename_group_service,
    update_cantiere_service,
    update_cliente_service,
)
from services.costi_service import create_costo_service, delete_costo_service, update_costo_service
from services.fatture_service import create_fattura_service, delete_fattura_service, update_fattura_service
from ui import theme
from ui.widgets import button, conferma, errore, label
from utils.validators import CATEGORIE_COSTO

# Etichette "umane" degli stati -> valore salvato nel database
STATI_UI = [("Da incassare", "Pendente"), ("Pagata", "Pagato"), ("Non pagata (insoluta)", "Non pagato")]
TAG_TASK = ["Generale", "Amministrazione", "Contabilità", "Cantiere", "Priorità alta"]


# --- Utilità comuni ---------------------------------------------------------------

def parse_importo(testo: str) -> float:
    """Accetta '1250', '1250,50', '1.250,50', '€ 1.250'."""
    pulito = (testo or "").replace("€", "").replace(" ", "").strip()
    if not pulito:
        raise ValueError("Scrivi l'importo.")
    if "," in pulito:
        pulito = pulito.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", pulito):
        pulito = pulito.replace(".", "")  # 1.250 = milleduecentocinquanta
    try:
        valore = float(pulito)
    except ValueError as exc:
        raise ValueError("L'importo non è un numero valido (esempio: 1.250,50).") from exc
    if valore < 0:
        raise ValueError("L'importo non può essere negativo.")
    return valore


def date_field(iso: str | None = None) -> QDateEdit:
    field = QDateEdit()
    field.setCalendarPopup(True)
    field.setDisplayFormat("dd/MM/yyyy")
    set_date(field, iso)
    return field


def set_date(field: QDateEdit, iso: str | None) -> None:
    qd = QDate.fromString(iso, "yyyy-MM-dd") if iso else QDate.currentDate()
    field.setDate(qd if qd.isValid() else QDate.currentDate())


def iso(field: QDateEdit) -> str:
    return field.date().toString("yyyy-MM-dd")


def select_data(combo: QComboBox, value) -> None:
    idx = combo.findData(value)
    combo.setCurrentIndex(idx if idx >= 0 else 0)


class BaseDialog(QDialog):
    """Finestra con titolo, modulo e pulsanti in basso (Elimina a sinistra, Annulla/Salva a destra)."""

    def __init__(self, parent, title: str, subtitle: str = "", width: int = 520, can_delete: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        root.addWidget(label(title, "pageTitle"))
        if subtitle:
            root.addWidget(label(subtitle, "pageSubtitle", wrap=True))

        self.form = QFormLayout()
        self.form.setSpacing(12)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(self.form)

        buttons = QHBoxLayout()
        if can_delete:
            buttons.addWidget(button("Elimina", "danger", self._on_delete))
        buttons.addStretch()
        buttons.addWidget(button("Annulla", None, self.reject))
        self.btn_save = button("Salva", "primary", self._on_save)
        self.btn_save.setDefault(True)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

    def add_row(self, text: str, widget) -> None:
        self.form.addRow(label(text, "fieldLabel"), widget)

    def _on_save(self) -> None:
        try:
            self.save()
        except Exception as exc:  # mostra l'errore senza chiudere la finestra
            errore(self, exc)
            return
        self.accept()

    def _on_delete(self) -> None:
        try:
            if self.delete():
                self.accept()
        except Exception as exc:
            errore(self, exc)

    # da implementare
    def save(self) -> None:
        raise NotImplementedError

    def delete(self) -> bool:
        return False


def _row(*widgets, stretch_first: bool = True) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    for i, widget in enumerate(widgets):
        lay.addWidget(widget, 1 if (i == 0 and stretch_first) else 0)
    return w


# --- Fattura -------------------------------------------------------------------------

class FatturaDialog(BaseDialog):
    SCADENZE = [("Nessuna scadenza", None), ("30 giorni", 30), ("60 giorni", 60),
                ("90 giorni", 90), ("Scegli una data…", "data")]

    def __init__(self, parent=None, fattura: dict | None = None):
        super().__init__(
            parent,
            "Modifica fattura" if fattura else "Nuova fattura",
            "I campi con * sono obbligatori.",
            can_delete=fattura is not None,
        )
        self.fattura = fattura

        self.combo_cliente = QComboBox()
        self.combo_cliente.currentIndexChanged.connect(self._load_cantieri)
        self.add_row("Cliente *", _row(self.combo_cliente, button("+ Nuovo", None, self._nuovo_cliente)))

        self.combo_cantiere = QComboBox()
        self.add_row("Cantiere", _row(self.combo_cantiere, button("+ Nuovo", None, self._nuovo_cantiere)))

        self.input_numero = QLineEdit()
        self.input_numero.setPlaceholderText("es. 28/2026")
        self.add_row("Numero fattura", self.input_numero)

        self.input_importo = QLineEdit()
        self.input_importo.setPlaceholderText("es. 1.250,00")
        self.add_row("Importo € *", self.input_importo)

        self.input_data = date_field()
        self.input_data.dateChanged.connect(self._update_scadenza_preview)
        self.add_row("Data fattura *", self.input_data)

        self.combo_scadenza = QComboBox()
        for testo, valore in self.SCADENZE:
            self.combo_scadenza.addItem(testo, valore)
        self.combo_scadenza.currentIndexChanged.connect(self._update_scadenza_preview)
        self.input_scadenza = date_field()
        self.add_row("Scadenza", _row(self.combo_scadenza, self.input_scadenza, stretch_first=False))

        self.combo_stato = QComboBox()
        for testo, valore in STATI_UI:
            self.combo_stato.addItem(testo, valore)
        self.combo_stato.currentIndexChanged.connect(self._update_pagamento)
        self.input_pagata_il = date_field()
        self.lbl_pagata_il = label("pagata il", "muted")
        self.add_row("Stato", _row(self.combo_stato, self.lbl_pagata_il, self.input_pagata_il, stretch_first=False))

        self.input_note = QTextEdit()
        self.input_note.setPlaceholderText("Note (facoltative)")
        self.input_note.setFixedHeight(80)
        self.add_row("Note", self.input_note)

        self._load_clienti()
        if fattura:
            self._fill(fattura)
        self._update_scadenza_preview()
        self._update_pagamento()

    # caricamento combo
    def _load_clienti(self, select_id=None) -> None:
        self.combo_cliente.blockSignals(True)
        self.combo_cliente.clear()
        self.combo_cliente.addItem("Scegli il cliente…", None)
        for c in get_all_clienti():
            testo = f"{c['nome']}  ·  {c['gruppo_nome']}" if c.get("gruppo_nome") else c["nome"]
            self.combo_cliente.addItem(testo, c["id"])
        self.combo_cliente.blockSignals(False)
        select_data(self.combo_cliente, select_id)
        self._load_cantieri()

    def _load_cantieri(self, *_args, select_id=None) -> None:
        self.combo_cantiere.clear()
        self.combo_cantiere.addItem("Nessun cantiere", None)
        cliente_id = self.combo_cliente.currentData()
        if cliente_id is not None:
            for ca in get_cantieri_by_cliente(cliente_id):
                self.combo_cantiere.addItem(ca["nome"], ca["id"])
        select_data(self.combo_cantiere, select_id)

    def _nuovo_cliente(self) -> None:
        dlg = ClienteDialog(self)
        if dlg.exec():
            self._load_clienti(select_id=dlg.saved_id)

    def _nuovo_cantiere(self) -> None:
        dlg = CantiereDialog(self, cliente_id=self.combo_cliente.currentData())
        if dlg.exec():
            if dlg.saved_cliente_id != self.combo_cliente.currentData():
                select_data(self.combo_cliente, dlg.saved_cliente_id)
            self._load_cantieri(select_id=dlg.saved_id)

    def _fill(self, f: dict) -> None:
        select_data(self.combo_cliente, f.get("cliente_id"))
        self._load_cantieri(select_id=f.get("cantiere_id"))
        self.input_numero.setText(f.get("numero_fattura") or "")
        self.input_importo.setText(theme.fmt_euro(f.get("importo")).replace("€ ", ""))
        set_date(self.input_data, f.get("data_inserimento"))
        if f.get("data_scadenza"):
            self.combo_scadenza.setCurrentIndex(len(self.SCADENZE) - 1)
            set_date(self.input_scadenza, f["data_scadenza"])
        select_data(self.combo_stato, f.get("stato"))
        if f.get("data_estinzione"):
            set_date(self.input_pagata_il, f["data_estinzione"])
        self.input_note.setPlainText(f.get("note") or "")

    def _update_scadenza_preview(self, *_args) -> None:
        scelta = self.combo_scadenza.currentData()
        if scelta is None:
            self.input_scadenza.setVisible(False)
        elif scelta == "data":
            self.input_scadenza.setVisible(True)
            self.input_scadenza.setEnabled(True)
        else:
            self.input_scadenza.setVisible(True)
            self.input_scadenza.setEnabled(False)  # calcolata in automatico
            self.input_scadenza.setDate(self.input_data.date().addDays(int(scelta)))

    def _update_pagamento(self, *_args) -> None:
        pagata = self.combo_stato.currentData() == "Pagato"
        self.lbl_pagata_il.setVisible(pagata)
        self.input_pagata_il.setVisible(pagata)

    def save(self) -> None:
        cliente_id = self.combo_cliente.currentData()
        if cliente_id is None:
            raise ValueError("Scegli il cliente.")
        dati = dict(
            cliente_id=cliente_id,
            cantiere_id=self.combo_cantiere.currentData(),
            numero_fattura=self.input_numero.text().strip() or None,
            importo=parse_importo(self.input_importo.text()),
            stato=self.combo_stato.currentData(),
            data_inserimento=iso(self.input_data),
            data_scadenza=iso(self.input_scadenza) if self.combo_scadenza.currentData() is not None else None,
            data_estinzione=iso(self.input_pagata_il) if self.combo_stato.currentData() == "Pagato" else None,
            note=self.input_note.toPlainText().strip() or None,
        )
        if self.fattura:
            update_fattura_service(fattura_id=self.fattura["id"], **dati)
        else:
            create_fattura_service(**dati)

    def delete(self) -> bool:
        numero = self.fattura.get("numero_fattura") or f"ID {self.fattura['id']}"
        if not conferma(self, "Elimina fattura", f"Eliminare definitivamente la fattura {numero}?"):
            return False
        delete_fattura_service(self.fattura["id"])
        return True


# --- Costo ----------------------------------------------------------------------------

class CostoDialog(BaseDialog):
    def __init__(self, parent=None, costo: dict | None = None):
        super().__init__(
            parent,
            "Modifica costo" if costo else "Nuovo costo",
            "Collega il costo a un cantiere per sapere quanto rende. Se è una spesa generale (affitto, carburante…) lascia «Nessuno».",
            can_delete=costo is not None,
        )
        self.costo = costo

        self.input_data = date_field()
        self.add_row("Data *", self.input_data)

        self.input_descrizione = QLineEdit()
        self.input_descrizione.setPlaceholderText("es. Cemento, noleggio escavatore…")
        self.add_row("Descrizione *", self.input_descrizione)

        self.input_importo = QLineEdit()
        self.input_importo.setPlaceholderText("es. 350,00")
        self.add_row("Importo € *", self.input_importo)

        self.combo_categoria = QComboBox()
        self.combo_categoria.addItems(CATEGORIE_COSTO)
        self.add_row("Categoria", self.combo_categoria)

        self.combo_cliente = QComboBox()
        self.combo_cliente.currentIndexChanged.connect(self._load_cantieri)
        self.add_row("Cliente", self.combo_cliente)

        self.combo_cantiere = QComboBox()
        self.add_row("Cantiere", self.combo_cantiere)

        self.input_note = QTextEdit()
        self.input_note.setPlaceholderText("Note (facoltative)")
        self.input_note.setFixedHeight(70)
        self.add_row("Note", self.input_note)

        self.combo_cliente.blockSignals(True)
        self.combo_cliente.addItem("Nessuno (spesa generale)", None)
        for c in get_all_clienti():
            self.combo_cliente.addItem(c["nome"], c["id"])
        self.combo_cliente.blockSignals(False)
        self._load_cantieri()

        if costo:
            set_date(self.input_data, costo.get("data"))
            self.input_descrizione.setText(costo.get("descrizione") or "")
            self.input_importo.setText(theme.fmt_euro(costo.get("importo")).replace("€ ", ""))
            cat = costo.get("categoria")
            if cat and self.combo_categoria.findText(cat) < 0:
                self.combo_categoria.addItem(cat)
            if cat:
                self.combo_categoria.setCurrentText(cat)
            select_data(self.combo_cliente, costo.get("cliente_id"))
            self._load_cantieri(select_id=costo.get("cantiere_id"))
            self.input_note.setPlainText(costo.get("note") or "")

    def _load_cantieri(self, *_args, select_id=None) -> None:
        self.combo_cantiere.clear()
        self.combo_cantiere.addItem("Nessun cantiere", None)
        cliente_id = self.combo_cliente.currentData()
        self.combo_cantiere.setEnabled(cliente_id is not None)
        if cliente_id is not None:
            for ca in get_cantieri_by_cliente(cliente_id):
                self.combo_cantiere.addItem(ca["nome"], ca["id"])
        select_data(self.combo_cantiere, select_id)

    def save(self) -> None:
        dati = dict(
            data=iso(self.input_data),
            descrizione=self.input_descrizione.text(),
            importo=parse_importo(self.input_importo.text()),
            categoria=self.combo_categoria.currentText(),
            cliente_id=self.combo_cliente.currentData(),
            cantiere_id=self.combo_cantiere.currentData(),
            note=self.input_note.toPlainText().strip() or None,
        )
        if self.costo:
            update_costo_service(self.costo["id"], **dati)
        else:
            create_costo_service(**dati)

    def delete(self) -> bool:
        if not conferma(self, "Elimina costo", f"Eliminare il costo «{self.costo['descrizione']}»?"):
            return False
        delete_costo_service(self.costo["id"])
        return True


# --- Cliente ----------------------------------------------------------------------------

class ClienteDialog(BaseDialog):
    def __init__(self, parent=None, cliente: dict | None = None):
        super().__init__(parent, "Modifica cliente" if cliente else "Nuovo cliente",
                         can_delete=cliente is not None, width=480)
        self.cliente = cliente
        self.saved_id = cliente["id"] if cliente else None

        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("es. Edil Rossi Srl")
        self.add_row("Nome *", self.input_nome)

        self.combo_gruppo = QComboBox()
        self.add_row("Gruppo", _row(self.combo_gruppo, button("+ Nuovo", None, self._nuovo_gruppo)))

        self.input_email = QLineEdit()
        self.add_row("Email", self.input_email)
        self.input_telefono = QLineEdit()
        self.add_row("Telefono", self.input_telefono)
        self.input_note = QTextEdit()
        self.input_note.setFixedHeight(70)
        self.add_row("Note", self.input_note)

        self._load_gruppi(cliente.get("group_id") if cliente else None)
        if cliente:
            self.input_nome.setText(cliente.get("nome") or "")
            self.input_email.setText(cliente.get("email") or "")
            self.input_telefono.setText(cliente.get("telefono") or "")
            self.input_note.setPlainText(cliente.get("note") or "")

    def _load_gruppi(self, select_id=None) -> None:
        self.combo_gruppo.clear()
        self.combo_gruppo.addItem("Nessun gruppo", None)
        for g in get_all_groups():
            self.combo_gruppo.addItem(g["nome"], g["id"])
        select_data(self.combo_gruppo, select_id)

    def _nuovo_gruppo(self) -> None:
        nome, ok = QInputDialog.getText(self, "Nuovo gruppo", "Nome del gruppo:")
        if ok and nome.strip():
            try:
                self._load_gruppi(create_group_service(nome))
            except Exception as exc:
                errore(self, exc)

    def save(self) -> None:
        dati = dict(
            nome=self.input_nome.text(),
            group_id=self.combo_gruppo.currentData(),
            email=self.input_email.text().strip() or None,
            telefono=self.input_telefono.text().strip() or None,
            note=self.input_note.toPlainText().strip() or None,
        )
        if self.cliente:
            update_cliente_service(self.cliente["id"], **dati)
        else:
            self.saved_id = create_cliente_service(**dati)

    def delete(self) -> bool:
        if not conferma(self, "Elimina cliente", f"Eliminare il cliente «{self.cliente['nome']}» e i suoi cantieri?"):
            return False
        delete_cliente_service(self.cliente["id"])
        return True


# --- Cantiere ---------------------------------------------------------------------------

class CantiereDialog(BaseDialog):
    def __init__(self, parent=None, cantiere: dict | None = None, cliente_id: int | None = None):
        super().__init__(parent, "Modifica cantiere" if cantiere else "Nuovo cantiere",
                         can_delete=cantiere is not None, width=480)
        self.cantiere = cantiere
        self.saved_id = cantiere["id"] if cantiere else None
        self.saved_cliente_id = cantiere["cliente_id"] if cantiere else cliente_id

        self.combo_cliente = QComboBox()
        self.combo_cliente.addItem("Scegli il cliente…", None)
        for c in get_all_clienti():
            self.combo_cliente.addItem(c["nome"], c["id"])
        select_data(self.combo_cliente, self.saved_cliente_id)
        self.add_row("Cliente *", self.combo_cliente)

        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("es. Villa Ghedi")
        self.add_row("Nome cantiere *", self.input_nome)
        self.input_localita = QLineEdit()
        self.add_row("Località", self.input_localita)
        self.input_indirizzo = QLineEdit()
        self.add_row("Indirizzo", self.input_indirizzo)
        self.input_note = QTextEdit()
        self.input_note.setFixedHeight(70)
        self.add_row("Note", self.input_note)

        if cantiere:
            self.input_nome.setText(cantiere.get("nome") or "")
            self.input_localita.setText(cantiere.get("localita") or "")
            self.input_indirizzo.setText(cantiere.get("indirizzo") or "")
            self.input_note.setPlainText(cantiere.get("note") or "")

    def save(self) -> None:
        dati = dict(
            cliente_id=self.combo_cliente.currentData(),
            nome=self.input_nome.text(),
            localita=self.input_localita.text().strip() or None,
            indirizzo=self.input_indirizzo.text().strip() or None,
            note=self.input_note.toPlainText().strip() or None,
        )
        if self.cantiere:
            update_cantiere_service(self.cantiere["id"], **dati)
        else:
            self.saved_id = create_cantiere_service(**dati)
        self.saved_cliente_id = dati["cliente_id"]

    def delete(self) -> bool:
        if not conferma(self, "Elimina cantiere",
                        f"Eliminare il cantiere «{self.cantiere['nome']}»?\nLe fatture e i costi collegati restano, senza cantiere."):
            return False
        delete_cantiere_service(self.cantiere["id"])
        return True


# --- Gruppi -----------------------------------------------------------------------------

class GruppiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gruppi clienti")
        self.setMinimumSize(420, 420)
        self.changed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(14)
        root.addWidget(label("Gruppi clienti", "pageTitle"))
        root.addWidget(label("Eliminando un gruppo i suoi clienti restano, senza gruppo.", "pageSubtitle", wrap=True))

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(lambda *_: self._rinomina())
        root.addWidget(self.lista, 1)

        row = QHBoxLayout()
        row.addWidget(button("+ Aggiungi", "primary", self._aggiungi))
        row.addWidget(button("Rinomina", None, self._rinomina))
        row.addWidget(button("Elimina", "danger", self._elimina))
        row.addStretch()
        row.addWidget(button("Chiudi", None, self.accept))
        root.addLayout(row)
        self._load()

    def _load(self) -> None:
        self.lista.clear()
        for g in get_all_groups():
            item = QListWidgetItem(g["nome"])
            item.setData(Qt.ItemDataRole.UserRole, g["id"])
            self.lista.addItem(item)

    def _selected(self):
        item = self.lista.currentItem()
        if item is None:
            errore(self, "Seleziona prima un gruppo dalla lista.")
        return item

    def _aggiungi(self) -> None:
        nome, ok = QInputDialog.getText(self, "Nuovo gruppo", "Nome del gruppo:")
        if ok and nome.strip():
            try:
                create_group_service(nome)
                self.changed = True
                self._load()
            except Exception as exc:
                errore(self, exc)

    def _rinomina(self) -> None:
        item = self._selected()
        if item is None:
            return
        nome, ok = QInputDialog.getText(self, "Rinomina gruppo", "Nuovo nome:", text=item.text())
        if ok and nome.strip():
            try:
                rename_group_service(item.data(Qt.ItemDataRole.UserRole), nome)
                self.changed = True
                self._load()
            except Exception as exc:
                errore(self, exc)

    def _elimina(self) -> None:
        item = self._selected()
        if item is None:
            return
        if conferma(self, "Elimina gruppo", f"Eliminare il gruppo «{item.text()}»?"):
            delete_group_service(item.data(Qt.ItemDataRole.UserRole))
            self.changed = True
            self._load()


# --- Attività ---------------------------------------------------------------------------

class TaskDialog(BaseDialog):
    def __init__(self, parent=None, task: dict | None = None, data_iso: str | None = None):
        super().__init__(parent, "Modifica attività" if task else "Nuova attività",
                         can_delete=task is not None, width=460)
        self.task = task

        self.input_titolo = QLineEdit()
        self.input_titolo.setPlaceholderText("es. Chiamare il commercialista")
        self.add_row("Cosa fare *", self.input_titolo)

        self.input_data = date_field(data_iso or date.today().isoformat())
        self.add_row("Giorno *", self.input_data)

        self.input_orario = QLineEdit()
        self.input_orario.setPlaceholderText("es. 14:30 (facoltativo)")
        self.add_row("Orario", self.input_orario)

        self.combo_tag = QComboBox()
        self.combo_tag.addItems(TAG_TASK)
        self.add_row("Categoria", self.combo_tag)

        self.input_note = QTextEdit()
        self.input_note.setFixedHeight(70)
        self.add_row("Note", self.input_note)

        if task:
            self.input_titolo.setText(task.get("titolo") or "")
            set_date(self.input_data, task.get("data"))
            self.input_orario.setText(task.get("orario") or "")
            tag = task.get("tag")
            if tag and self.combo_tag.findText(tag) < 0:
                self.combo_tag.addItem(tag)
            if tag:
                self.combo_tag.setCurrentText(tag)
            self.input_note.setPlainText(task.get("note") or "")

    def save(self) -> None:
        titolo = self.input_titolo.text().strip()
        if not titolo:
            raise ValueError("Scrivi cosa c'è da fare.")
        orario = self.input_orario.text().strip().replace(".", ":") or None
        if orario:
            m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", orario)
            if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
                raise ValueError("Orario non valido: usa il formato 14:30.")
            orario = f"{int(m.group(1)):02d}:{m.group(2) or '00'}"
        note = self.input_note.toPlainText().strip() or None
        if self.task:
            update_task(self.task["id"], iso(self.input_data), orario, titolo, self.combo_tag.currentText(), note)
        else:
            create_task(iso(self.input_data), orario, titolo, self.combo_tag.currentText(), note)

    def delete(self) -> bool:
        if not conferma(self, "Elimina attività", "Eliminare questa attività?"):
            return False
        delete_task(self.task["id"])
        return True
