"""Mattoncini grafici riutilizzati da tutte le schermate."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme


def button(text: str, kind: str | None = None, on_click=None) -> QPushButton:
    """Crea un pulsante. kind: 'primary', 'success', 'danger', 'link' oppure None."""
    btn = QPushButton(text)
    if kind:
        btn.setObjectName(kind)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click is not None:
        btn.clicked.connect(on_click)
    return btn


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def errore(parent, exc: Exception | str) -> None:
    QMessageBox.warning(parent, "Attenzione", str(exc))


def conferma(parent, titolo: str, testo: str) -> bool:
    risposta = QMessageBox.question(
        parent, titolo, testo,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return risposta == QMessageBox.StandardButton.Yes


class Card(QFrame):
    """Riquadro bianco con titolo opzionale e nota a destra."""

    def __init__(self, title: str | None = None, hint: str | None = None):
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(20, 18, 20, 18)
        self.body.setSpacing(12)

        self.title_label = None
        self.hint_label = None
        if title is not None:
            head = QHBoxLayout()
            self.title_label = label(title, "cardTitle")
            self.hint_label = label(hint or "", "cardHint")
            head.addWidget(self.title_label)
            head.addStretch()
            head.addWidget(self.hint_label)
            self.body.addLayout(head)


class KpiCard(QFrame):
    """Riquadro con un numero grande. accent: 'arancio', 'rosso', 'verde', 'blu'."""

    COLORI = {
        "arancio": (theme.AMBER, theme.TEXT),
        "rosso": (theme.RED, theme.RED_DARK),
        "verde": (theme.GREEN, theme.GREEN_DARK),
        "blu": (theme.BLUE, theme.TEXT),
    }

    def __init__(self, title: str, accent: str = "blu"):
        super().__init__()
        self.setObjectName("card")
        bordo, colore_valore = self.COLORI.get(accent, self.COLORI["blu"])
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {theme.SURFACE}; border: 1px solid {theme.BORDER};"
            f" border-top: 4px solid {bordo}; border-radius: 14px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        self.title_label = label(title, "kpiLabel")
        self.value_label = label("—", "kpiValue")
        self.value_label.setStyleSheet(f"color: {colore_valore};")
        self.hint_label = label("", "kpiHint", wrap=True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)

    def set_values(self, value: str, hint: str = "", title: str | None = None) -> None:
        self.value_label.setText(value)
        self.hint_label.setText(hint)
        if title is not None:
            self.title_label.setText(title)


class Pill(QWidget):
    """Etichetta colorata arrotondata, da mettere dentro una cella di tabella."""

    def __init__(self, text: str, color: str = "grigio"):
        super().__init__()
        bg, fg = theme.PILL.get(color, theme.PILL["grigio"])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 10px;"
            "padding: 3px 10px; font-size: 12px; font-weight: 700;"
        )
        layout.addWidget(lbl)
        layout.addStretch()
        # i clic passano alla tabella (così il doppio clic sulla riga funziona)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def make_table(headers: list[str], stretch_cols: tuple[int, ...] = ()) -> QTableWidget:
    """Tabella in sola lettura, selezione per riga, senza griglia."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels([h.upper() for h in headers])
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(44)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setShowGrid(False)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setWordWrap(False)
    header = table.horizontalHeader()
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setHighlightSections(False)
    for col in range(len(headers)):
        mode = QHeaderView.ResizeMode.Stretch if col in stretch_cols else QHeaderView.ResizeMode.ResizeToContents
        header.setSectionResizeMode(col, mode)
    return table


class BarChart(QWidget):
    """Grafico a barre semplice disegnato a mano (niente matplotlib).

    set_data([(etichetta, valore, colore), ...])
    """

    def __init__(self):
        super().__init__()
        self.data: list[tuple[str, float, str]] = []
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list[tuple[str, float, str]]) -> None:
        self.data = data
        self.update()

    def paintEvent(self, event):  # noqa: N802 (nome imposto da Qt)
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        top_pad, bottom_pad, gap = 24, 26, 14
        n = len(self.data)
        bar_w = max(10.0, (w - gap * (n - 1)) / n)
        area_h = h - top_pad - bottom_pad
        massimo = max((v for _, v, _ in self.data), default=0) or 1

        font_val = QFont(self.font())
        font_val.setPointSizeF(max(8.0, font_val.pointSizeF() - 1))
        font_val.setBold(True)
        font_lbl = QFont(self.font())
        font_lbl.setPointSizeF(max(8.0, font_lbl.pointSizeF() - 1))

        for i, (etichetta, valore, colore) in enumerate(self.data):
            x = i * (bar_w + gap)
            bar_h = max(2.0, area_h * (valore / massimo)) if valore else 2.0
            y = top_pad + area_h - bar_h

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(colore))
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 5, 5)

            p.setPen(QColor(theme.TEXT))
            p.setFont(font_val)
            testo = theme.fmt_euro(valore, 0).replace("€ ", "")
            p.drawText(QRectF(x - 10, y - 20, bar_w + 20, 18), Qt.AlignmentFlag.AlignCenter, testo)

            p.setPen(QColor(theme.TEXT_MUTED))
            p.setFont(font_lbl)
            p.drawText(QRectF(x - 10, h - bottom_pad + 6, bar_w + 20, 18), Qt.AlignmentFlag.AlignCenter, etichetta)
        p.end()


class PageHeader(QWidget):
    """Titolo grande + sottotitolo a sinistra, pulsanti a destra."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title_label = label(title, "pageTitle")
        self.subtitle_label = label(subtitle, "pageSubtitle")
        texts.addWidget(self.title_label)
        texts.addWidget(self.subtitle_label)

        layout.addLayout(texts)
        layout.addStretch()
        self.actions = layout

    def add_action(self, btn: QPushButton) -> QPushButton:
        self.actions.addWidget(btn)
        return btn


class Page(QWidget):
    """Base di ogni schermata: margini standard e metodo refresh()."""

    def __init__(self, app_window=None):
        super().__init__()
        self.setObjectName("page")
        self.app_window = app_window
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(30, 26, 30, 26)
        self.root.setSpacing(18)

    def refresh(self) -> None:  # da implementare nelle schermate
        pass

    def notify_changed(self) -> None:
        """Avvisa la finestra principale che i dati sono cambiati."""
        if self.app_window is not None:
            self.app_window.data_changed()
