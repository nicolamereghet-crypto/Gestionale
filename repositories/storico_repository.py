from database.db import get_connection


def create_storico(
    fattura_id: int | None,
    azione: str,
    dettagli: str,
    data_evento: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO storico (fattura_id, azione, dettagli, data_evento)
            VALUES (?, ?, ?, ?)
        """, (fattura_id, azione, dettagli, data_evento))
        conn.commit()
        return cursor.lastrowid


def get_storico(
    search_text: str = "",
    azione_filter: str = "Tutte",
) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, fattura_id, azione, dettagli, data_evento
            FROM storico
            WHERE 1=1
        """
        params = []

        if search_text.strip():
            query += " AND LOWER(dettagli) LIKE ?"
            params.append(f"%{search_text.strip().lower()}%")

        if azione_filter != "Tutte":
            query += " AND azione = ?"
            params.append(azione_filter)

        query += " ORDER BY id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]