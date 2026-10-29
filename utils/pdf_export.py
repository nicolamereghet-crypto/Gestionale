from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def export_fatture_to_pdf(
    filepath: str,
    fatture: list[dict],
    filtro_gruppo: str,
    filtro_cliente: str,
    filtro_stato: str,
) -> None:
    path = Path(filepath)
    c = canvas.Canvas(str(path), pagesize=A4)

    width, height = A4
    x_margin = 35
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, "Gestionale Fatture - Esportazione PDF")

    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, f"Filtro gruppo: {filtro_gruppo or 'Tutti'}")
    y -= 15
    c.drawString(x_margin, y, f"Filtro cliente: {filtro_cliente or 'Tutti'}")
    y -= 15
    c.drawString(x_margin, y, f"Filtro stato: {filtro_stato or 'Tutti'}")

    y -= 25
    c.setFont("Helvetica-Bold", 9)
    c.drawString(35, y, "ID")
    c.drawString(60, y, "Gruppo")
    c.drawString(120, y, "Cliente")
    c.drawString(210, y, "Cantiere")
    c.drawString(285, y, "Numero")
    c.drawString(345, y, "Importo")
    c.drawString(405, y, "Stato")
    c.drawString(455, y, "Ins.")
    c.drawString(505, y, "Est.")

    y -= 10
    c.line(35, y, width - 35, y)
    y -= 15

    c.setFont("Helvetica", 8)

    for fattura in fatture:
        if y < 60:
            c.showPage()
            y = height - 40

            c.setFont("Helvetica-Bold", 9)
            c.drawString(35, y, "ID")
            c.drawString(60, y, "Gruppo")
            c.drawString(120, y, "Cliente")
            c.drawString(210, y, "Cantiere")
            c.drawString(285, y, "Numero")
            c.drawString(345, y, "Importo")
            c.drawString(405, y, "Stato")
            c.drawString(455, y, "Ins.")
            c.drawString(505, y, "Est.")
            y -= 10
            c.line(35, y, width - 35, y)
            y -= 15
            c.setFont("Helvetica", 8)

        gruppo = str(fattura.get("gruppo_nome") or "")[:12]
        cliente = str(fattura.get("cliente_nome") or "")[:16]
        cantiere = str(fattura.get("cantiere_nome") or "")[:14]
        numero = str(fattura.get("numero_fattura") or "")[:10]
        stato = str(fattura.get("stato") or "")[:10]
        data_ins = str(fattura.get("data_inserimento") or "")[:10]
        data_est = str(fattura.get("data_estinzione") or "")[:10]

        c.drawString(35, y, str(fattura["id"]))
        c.drawString(60, y, gruppo)
        c.drawString(120, y, cliente)
        c.drawString(210, y, cantiere)
        c.drawString(285, y, numero)
        c.drawRightString(390, y, f"{fattura['importo']:.2f} €")
        c.drawString(405, y, stato)
        c.drawString(455, y, data_ins)
        c.drawString(505, y, data_est)

        y -= 16

    c.save()


def export_dashboard_to_pdf(
    filepath: str,
    anno: str,
    mese_label: str,
    dashboard_data: dict,
    monthly_trend: list[float],
) -> None:
    path = Path(filepath)
    c = canvas.Canvas(str(path), pagesize=A4)

    width, height = A4
    x_margin = 40
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, "Dashboard Fatture - Esportazione PDF")

    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, f"Anno selezionato: {anno}")
    y -= 15
    c.drawString(x_margin, y, f"Mese selezionato: {mese_label}")
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, "Riepilogo economico")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, f"Periodo selezionato: {dashboard_data['totale_periodo']:.2f} €")
    y -= 15
    c.drawString(x_margin, y, f"Totale annuo: {dashboard_data['totale_annuo']:.2f} €")
    y -= 15
    c.drawString(x_margin, y, f"Totale pagato: {dashboard_data['totale_pagato']:.2f} €")
    y -= 15
    c.drawString(x_margin, y, f"Da incassare: {dashboard_data['totale_da_incassare']:.2f} €")
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, "Importi per stato")
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Stato")
    c.drawString(180, y, "Numero fatture")
    c.drawString(320, y, "Importo totale")
    y -= 10
    c.line(40, y, width - 40, y)
    y -= 15

    c.setFont("Helvetica", 10)
    for stato in ["Pagato", "Pendente", "Non pagato"]:
        c.drawString(40, y, stato)
        c.drawString(180, y, str(dashboard_data["conteggio_stati"][stato]))
        c.drawRightString(420, y, f"{dashboard_data['importi_stati'][stato]:.2f} €")
        y -= 16

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, "Andamento mensile")
    y -= 20

    mesi = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]

    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Mese")
    c.drawString(250, y, "Totale importi")
    y -= 10
    c.line(40, y, width - 40, y)
    y -= 15

    c.setFont("Helvetica", 10)
    for mese_nome, valore in zip(mesi, monthly_trend):
        if y < 60:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Mese")
            c.drawString(250, y, "Totale importi")
            y -= 10
            c.line(40, y, width - 40, y)
            y -= 15
            c.setFont("Helvetica", 10)

        c.drawString(40, y, mese_nome)
        c.drawRightString(340, y, f"{valore:.2f} €")
        y -= 16

    c.save()