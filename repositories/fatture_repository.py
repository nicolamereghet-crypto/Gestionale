from database.db import get_connection


def get_fatture(
    group_id: int | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    stato: str | None = None,
) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                f.id,
                f.cliente_id,
                f.cantiere_id,
                f.numero_fattura,
                f.importo,
                f.stato,
                f.data_inserimento,
                f.data_scadenza,
                f.data_estinzione,
                f.note,
                c.nome AS cliente_nome,
                g.nome AS gruppo_nome,
                ca.nome AS cantiere_nome
            FROM fatture f
            JOIN clienti c ON f.cliente_id = c.id
            LEFT JOIN customer_groups g ON c.group_id = g.id
            LEFT JOIN cantieri ca ON f.cantiere_id = ca.id
            WHERE 1=1
        """
        params = []

        if group_id is not None:
            query += " AND c.group_id = ?"
            params.append(group_id)

        if cliente_id is not None:
            query += " AND f.cliente_id = ?"
            params.append(cliente_id)

        if cantiere_id is not None:
            query += " AND f.cantiere_id = ?"
            params.append(cantiere_id)

        if stato is not None and stato != "Tutti":
            query += " AND f.stato = ?"
            params.append(stato)

        query += " ORDER BY f.data_inserimento DESC, f.id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_fattura_by_id(fattura_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM fatture
            WHERE id = ?
        """, (fattura_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_fattura(
    cliente_id: int,
    cantiere_id: int | None,
    numero_fattura: str | None,
    importo: float,
    stato: str,
    data_inserimento: str,
    data_estinzione: str | None,
    note: str | None,
    data_scadenza: str | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fatture (
                cliente_id,
                cantiere_id,
                numero_fattura,
                importo,
                stato,
                data_inserimento,
                data_scadenza,
                data_estinzione,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente_id,
            cantiere_id,
            numero_fattura,
            importo,
            stato,
            data_inserimento,
            data_scadenza,
            data_estinzione,
            note,
        ))
        conn.commit()
        return cursor.lastrowid


def update_fattura(
    fattura_id: int,
    cliente_id: int,
    cantiere_id: int | None,
    numero_fattura: str | None,
    importo: float,
    stato: str,
    data_inserimento: str,
    data_estinzione: str | None,
    note: str | None,
    data_scadenza: str | None = None,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fatture
            SET cliente_id = ?,
                cantiere_id = ?,
                numero_fattura = ?,
                importo = ?,
                stato = ?,
                data_inserimento = ?,
                data_scadenza = ?,
                data_estinzione = ?,
                note = ?
            WHERE id = ?
        """, (
            cliente_id,
            cantiere_id,
            numero_fattura,
            importo,
            stato,
            data_inserimento,
            data_scadenza,
            data_estinzione,
            note,
            fattura_id,
        ))
        conn.commit()


def delete_fattura(fattura_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM fatture
            WHERE id = ?
        """, (fattura_id,))
        conn.commit()


def update_fattura_status(
    fattura_id: int,
    nuovo_stato: str,
    data_estinzione: str | None,
) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fatture
            SET stato = ?, data_estinzione = ?
            WHERE id = ?
        """, (nuovo_stato, data_estinzione, fattura_id))
        conn.commit()