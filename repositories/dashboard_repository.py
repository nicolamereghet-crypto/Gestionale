from datetime import date, datetime

from database.db import get_connection
from utils.validators import STATI_APERTI

_APERTI_SQL = "('" + "', '".join(STATI_APERTI) + "')"


def get_available_years() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT anno FROM (
                SELECT DISTINCT substr(data_inserimento, 1, 4) AS anno FROM fatture
                WHERE data_inserimento IS NOT NULL AND TRIM(data_inserimento) != ''
                UNION
                SELECT DISTINCT substr(data, 1, 4) AS anno FROM costi
                WHERE data IS NOT NULL AND TRIM(data) != ''
            )
            ORDER BY anno DESC
        """).fetchall()
        anni = [row["anno"] for row in rows if row["anno"]]
        anno_corrente = datetime.now().strftime("%Y")
        if anno_corrente not in anni:
            anni.insert(0, anno_corrente)
        return anni


def _filtro_periodo(colonna: str, selected_year: str, selected_month: str) -> tuple[str, list]:
    where = f"substr({colonna}, 1, 4) = ?"
    params = [selected_year]
    if selected_month != "Tutti":
        where += f" AND substr({colonna}, 6, 2) = ?"
        params.append(selected_month)
    return where, params


def get_dashboard_data(selected_year: str | None = None, selected_month: str = "Tutti") -> dict:
    """Riepilogo del periodo.

    Nota: `totale_da_incassare` ora considera TUTTE le fatture ancora aperte,
    di qualunque anno. Prima venivano contate solo quelle dell'anno
    selezionato, e una fattura del 2025 non pagata spariva guardando il 2026.
    Il valore limitato al periodo è in `da_incassare_periodo`.
    """
    if not selected_year:
        selected_year = datetime.now().strftime("%Y")
    oggi = date.today().isoformat()

    with get_connection() as conn:
        where, params = _filtro_periodo("data_inserimento", selected_year, selected_month)

        conteggio_stati = {"Pagato": 0, "Pendente": 0, "Non pagato": 0}
        importi_stati = {"Pagato": 0.0, "Pendente": 0.0, "Non pagato": 0.0}
        for row in conn.execute(f"""
            SELECT stato, COUNT(*) AS n, COALESCE(SUM(importo), 0) AS tot
            FROM fatture WHERE {where} GROUP BY stato
        """, params):
            if row["stato"] in conteggio_stati:
                conteggio_stati[row["stato"]] = row["n"]
                importi_stati[row["stato"]] = float(row["tot"])

        totale_periodo = sum(importi_stati.values())
        totale_pagato = importi_stati["Pagato"]
        da_incassare_periodo = importi_stati["Pendente"] + importi_stati["Non pagato"]

        totale_annuo = float(conn.execute("""
            SELECT COALESCE(SUM(importo), 0) FROM fatture
            WHERE substr(data_inserimento, 1, 4) = ?
        """, (selected_year,)).fetchone()[0])

        aperti = conn.execute(f"""
            SELECT COALESCE(SUM(importo), 0) AS tot,
                   COALESCE(SUM(CASE WHEN data_scadenza IS NOT NULL AND data_scadenza < ?
                                     THEN importo END), 0) AS scaduto,
                   COUNT(*) AS n,
                   COALESCE(SUM(CASE WHEN data_scadenza IS NOT NULL AND data_scadenza < ?
                                     THEN 1 END), 0) AS n_scadute
            FROM fatture WHERE stato IN {_APERTI_SQL}
        """, (oggi, oggi)).fetchone()

        where_c, params_c = _filtro_periodo("data", selected_year, selected_month)
        costi_periodo = float(conn.execute(
            f"SELECT COALESCE(SUM(importo), 0) FROM costi WHERE {where_c}", params_c
        ).fetchone()[0])

    return {
        "conteggio_stati": conteggio_stati,
        "importi_stati": importi_stati,
        "totale_periodo": totale_periodo,
        "totale_annuo": totale_annuo,
        "totale_pagato": totale_pagato,
        "totale_da_incassare": float(aperti["tot"]),
        "numero_fatture_aperte": aperti["n"],
        "totale_scaduto": float(aperti["scaduto"]),
        "numero_fatture_scadute": aperti["n_scadute"],
        "da_incassare_periodo": da_incassare_periodo,
        "costi_periodo": costi_periodo,
        "margine_periodo": totale_periodo - costi_periodo,
        "selected_year": selected_year,
        "selected_month": selected_month,
    }


def _trend_mensile(tabella: str, colonna_data: str, selected_year: str | None) -> list[float]:
    if not selected_year:
        selected_year = datetime.now().strftime("%Y")
    valori = [0.0] * 12
    with get_connection() as conn:
        for row in conn.execute(f"""
            SELECT substr({colonna_data}, 6, 2) AS mese, COALESCE(SUM(importo), 0) AS totale
            FROM {tabella}
            WHERE substr({colonna_data}, 1, 4) = ?
            GROUP BY mese
        """, (selected_year,)):
            mese = row["mese"]
            if mese and mese.isdigit() and 1 <= int(mese) <= 12:
                valori[int(mese) - 1] = float(row["totale"])
    return valori


def get_monthly_trend(selected_year: str | None = None) -> list[float]:
    """Totale fatturato per mese (12 valori)."""
    return _trend_mensile("fatture", "data_inserimento", selected_year)


def get_costi_monthly_trend(selected_year: str | None = None) -> list[float]:
    """Totale costi per mese (12 valori)."""
    return _trend_mensile("costi", "data", selected_year)


def get_crediti_aperti() -> list[dict]:
    """Fatture non ancora pagate, con i giorni di ritardo rispetto alla scadenza.

    Ordinate: prima le scadute (dalla più vecchia), poi le altre per scadenza,
    infine quelle senza scadenza.
    """
    oggi = date.today()
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT f.id, f.numero_fattura, f.importo, f.stato,
                   f.data_inserimento, f.data_scadenza,
                   c.nome AS cliente_nome, ca.nome AS cantiere_nome, g.nome AS gruppo_nome
            FROM fatture f
            JOIN clienti c ON f.cliente_id = c.id
            LEFT JOIN cantieri ca ON f.cantiere_id = ca.id
            LEFT JOIN customer_groups g ON c.group_id = g.id
            WHERE f.stato IN {_APERTI_SQL}
            ORDER BY f.data_scadenza IS NULL, f.data_scadenza, f.data_inserimento
        """).fetchall()

    risultato = []
    for row in rows:
        d = dict(row)
        if d["data_scadenza"]:
            delta = (oggi - date.fromisoformat(d["data_scadenza"])).days
            d["giorni_ritardo"] = max(delta, 0)
            d["scaduta"] = delta > 0
        else:
            d["giorni_ritardo"] = None
            d["scaduta"] = False
        # da sollecitare: scaduta, oppure segnata a mano come "Non pagato" (insoluta)
        d["da_sollecitare"] = d["scaduta"] or d["stato"] == "Non pagato"
        risultato.append(d)
    return risultato


def get_incassi_attesi(mesi: int = 6) -> list[dict]:
    """Quanto deve entrare e quando, raggruppato per mese di scadenza.

    Restituisce righe {"etichetta", "chiave", "importo", "numero"}:
    - "scadute": scadenza già passata, oppure fattura segnata come "Non pagato"
    - un elemento per ognuno dei prossimi `mesi` mesi (chiave "AAAA-MM")
    - "oltre": scadenza dopo l'ultimo mese mostrato
    - "senza_scadenza": fatture aperte senza data di scadenza
    """
    mesi_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
               "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    oggi = date.today()

    chiavi_mesi = []
    y, m = oggi.year, oggi.month
    for _ in range(mesi):
        chiavi_mesi.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1

    buckets = {"scadute": [0.0, 0], "oltre": [0.0, 0], "senza_scadenza": [0.0, 0]}
    buckets.update({k: [0.0, 0] for k in chiavi_mesi})

    for f in get_crediti_aperti():
        if f["da_sollecitare"]:
            key = "scadute"
        elif not f["data_scadenza"]:
            key = "senza_scadenza"
        else:
            mese = f["data_scadenza"][:7]
            key = mese if mese in buckets else "oltre"
        buckets[key][0] += float(f["importo"])
        buckets[key][1] += 1

    righe = [{"chiave": "scadute", "etichetta": "Scadute", "importo": buckets["scadute"][0], "numero": buckets["scadute"][1]}]
    for k in chiavi_mesi:
        anno, mese = k.split("-")
        righe.append({
            "chiave": k,
            "etichetta": f"{mesi_it[int(mese) - 1]} {anno}",
            "importo": buckets[k][0],
            "numero": buckets[k][1],
        })
    righe.append({"chiave": "oltre", "etichetta": "Più avanti", "importo": buckets["oltre"][0], "numero": buckets["oltre"][1]})
    righe.append({"chiave": "senza_scadenza", "etichetta": "Senza scadenza", "importo": buckets["senza_scadenza"][0], "numero": buckets["senza_scadenza"][1]})
    return righe


def get_margine_per_cantiere(selected_year: str | None = None) -> list[dict]:
    """Ricavi (fatture), costi e margine per ogni cantiere.

    Se `selected_year` è indicato, considera solo fatture e costi di quell'anno.
    """
    filtro_f = filtro_c = ""
    params: list = []
    if selected_year:
        filtro_f = "AND substr(f.data_inserimento, 1, 4) = ?"
        filtro_c = "AND substr(co.data, 1, 4) = ?"
        params = [selected_year, selected_year]

    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT ca.id, ca.nome AS cantiere_nome, c.nome AS cliente_nome,
                   COALESCE((SELECT SUM(f.importo) FROM fatture f
                             WHERE f.cantiere_id = ca.id {filtro_f}), 0) AS ricavi,
                   COALESCE((SELECT SUM(co.importo) FROM costi co
                             WHERE co.cantiere_id = ca.id {filtro_c}), 0) AS costi
            FROM cantieri ca
            JOIN clienti c ON ca.cliente_id = c.id
        """, params).fetchall()

    risultato = []
    for row in rows:
        d = dict(row)
        if not d["ricavi"] and not d["costi"]:
            continue
        d["margine"] = d["ricavi"] - d["costi"]
        d["margine_pct"] = (d["margine"] / d["ricavi"] * 100) if d["ricavi"] else None
        risultato.append(d)
    risultato.sort(key=lambda r: r["margine"], reverse=True)
    return risultato


def get_riepilogo_anno(anno: str | None = None) -> dict:
    """Numeri per la Home, riferiti all'anno indicato (default: anno corrente).

    - incassato: fatture PAGATE nell'anno (data di pagamento), anche se emesse prima
    - fatturato: fatture EMESSE nell'anno
    - costi: costi con data nell'anno
    - guadagno: fatturato - costi
    """
    if not anno:
        anno = datetime.now().strftime("%Y")
    with get_connection() as conn:
        incassato = conn.execute("""
            SELECT COALESCE(SUM(importo), 0) AS tot, COUNT(*) AS n FROM fatture
            WHERE stato = 'Pagato' AND substr(COALESCE(data_estinzione, data_inserimento), 1, 4) = ?
        """, (anno,)).fetchone()
        fatturato = float(conn.execute(
            "SELECT COALESCE(SUM(importo), 0) FROM fatture WHERE substr(data_inserimento, 1, 4) = ?", (anno,)
        ).fetchone()[0])
        costi = float(conn.execute(
            "SELECT COALESCE(SUM(importo), 0) FROM costi WHERE substr(data, 1, 4) = ?", (anno,)
        ).fetchone()[0])
    return {
        "anno": anno,
        "incassato": float(incassato["tot"]),
        "numero_pagate": incassato["n"],
        "fatturato": fatturato,
        "costi": costi,
        "guadagno": fatturato - costi,
    }
