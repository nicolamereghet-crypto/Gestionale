"""Attività: calendario a sinistra, cose da fare del giorno a destra."""
from datetime import date

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from repositories.tasks_repository import get_giorni_con_task, get_tasks_by_date, get_tasks_in_sospeso, toggle_task_done
from ui import theme
from ui.dialogs import TaskDialog
from ui.widgets import Card, Page, PageHeader, button, clear_layout, label


class AttivitaPage(Page):
    def __init__(self, app_window=None):
        super().__init__(app_window)

        header = PageHeader("Attività", "Scegli un giorno sul calendario. I giorni in grassetto blu hanno cose da fare.")
        header.add_action(button("Oggi", None, self._vai_oggi))
        header.add_action(button("+ Nuova attività", "primary", self._nuova))
        self.root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(16)
        cal_card = Card()
        self.calendar = QCalendarWidget()
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setMinimumSize(340, 300)
        self.calendar.selectionChanged.connect(self._render_giorno)
        self.calendar.currentPageChanged.connect(lambda *_: self._evidenzia_giorni())
        cal_card.body.addWidget(self.calendar)
        left.addWidget(cal_card)

        self.card_sospese = Card("⏰  Rimaste indietro", "giorni passati, non completate")
        self.list_sospese = QVBoxLayout()
        self.list_sospese.setSpacing(0)
        self.card_sospese.body.addLayout(self.list_sospese)
        left.addWidget(self.card_sospese)
        left.addStretch()
        body.addLayout(left, 2)

        self.card_giorno = Card("", "")
        self.list_giorno = QVBoxLayout()
        self.list_giorno.setSpacing(0)
        self.card_giorno.body.addLayout(self.list_giorno)
        self.card_giorno.body.addWidget(button("+ Aggiungi attività per questo giorno", None, self._nuova), 0,
                                        Qt.AlignmentFlag.AlignLeft)
        self.card_giorno.body.addStretch()
        body.addWidget(self.card_giorno, 3)

        self.root.addLayout(body, 1)

    def _giorno_iso(self) -> str:
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

    def refresh(self) -> None:
        self._evidenzia_giorni()
        self._render_giorno()
        self._render_sospese()

    def _evidenzia_giorni(self) -> None:
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())  # azzera
        anno, mese = self.calendar.yearShown(), self.calendar.monthShown()
        inizio = QDate(anno, mese, 1).addDays(-7)
        fine = QDate(anno, mese, 1).addMonths(1).addDays(7)
        fmt = QTextCharFormat()
        fmt.setFontWeight(700)
        fmt.setForeground(QColor(theme.BLUE))
        for giorno, da_fare in get_giorni_con_task(inizio.toString("yyyy-MM-dd"), fine.toString("yyyy-MM-dd")).items():
            if da_fare:
                self.calendar.setDateTextFormat(QDate.fromString(giorno, "yyyy-MM-dd"), fmt)

    def _render_giorno(self) -> None:
        giorno = self._giorno_iso()
        d = date.fromisoformat(giorno)
        titolo = "Oggi" if d == date.today() else f"{theme.GIORNI[d.weekday()]} {d.day} {theme.MESI[d.month - 1].lower()}"
        self.card_giorno.title_label.setText(titolo)

        tasks = get_tasks_by_date(giorno)
        fatte = sum(1 for t in tasks if t["done"])
        self.card_giorno.hint_label.setText(f"{fatte} su {len(tasks)} fatte" if tasks else "")
        clear_layout(self.list_giorno)
        if not tasks:
            self.list_giorno.addWidget(label("Niente in programma per questo giorno.", "emptyState"))
        for t in tasks:
            self.list_giorno.addWidget(self._row(t))

    def _render_sospese(self) -> None:
        sospese = get_tasks_in_sospeso(date.today().isoformat())
        clear_layout(self.list_sospese)
        self.card_sospese.setVisible(bool(sospese))
        for t in sospese[:8]:
            self.list_sospese.addWidget(self._row(t, mostra_data=True))
        if len(sospese) > 8:
            self.list_sospese.addWidget(label(f"…e altre {len(sospese) - 8}", "muted"))

    def _row(self, t: dict, mostra_data: bool = False) -> QWidget:
        row = QWidget()
        row.setObjectName("taskRow")
        row.setStyleSheet("QWidget#taskRow { border-bottom: 1px solid #f1f5f9; }")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(10)

        chk = QCheckBox()
        chk.setChecked(bool(t["done"]))
        chk.toggled.connect(lambda checked, tid=t["id"]: self._toggle(tid, checked))
        lay.addWidget(chk)

        quando = theme.fmt_data_breve(t["data"]) if mostra_data else (t.get("orario") or "—")
        ora = QLabel(quando)
        ora.setFixedWidth(44)
        ora.setStyleSheet(f"color: {theme.RED_DARK if mostra_data else theme.TEXT_MUTED}; font-size: 12px;")
        lay.addWidget(ora)

        testi = QVBoxLayout()
        testi.setSpacing(2)
        titolo = QLabel(t["titolo"])
        titolo.setWordWrap(True)
        if t["done"]:
            titolo.setStyleSheet(f"color: {theme.TEXT_SOFT}; text-decoration: line-through;")
        testi.addWidget(titolo)
        sotto = " · ".join(x for x in (t.get("tag"), t.get("note")) if x)
        if sotto and not mostra_data:
            s = QLabel(sotto)
            s.setWordWrap(True)
            s.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
            testi.addWidget(s)
        lay.addLayout(testi, 1)

        lay.addWidget(button("Modifica", "link", lambda _=False, task=t: self._modifica(task)))
        return row

    # --- azioni ------------------------------------------------------------------------------
    def _toggle(self, task_id: int, done: bool) -> None:
        toggle_task_done(task_id, done)
        QTimer.singleShot(0, self.notify_changed)

    def _vai_oggi(self) -> None:
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.showSelectedDate()

    def _nuova(self) -> None:
        if TaskDialog(self, data_iso=self._giorno_iso()).exec():
            self.notify_changed()

    def _modifica(self, task: dict) -> None:
        if TaskDialog(self, task=task).exec():
            self.notify_changed()
