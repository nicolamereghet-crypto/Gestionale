from database.db import get_connection


def get_costi(
    anno: str | None = None,
    mese: str | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    categoria: str | None = None,
) -> list[dict]:
    with get_connection() as conn:
        query = """
            SELECT co.id, co.data, co.descrizione, co.categoria, co.importo,
                   co.cliente_id, co.cantiere_id, co.pagato, co.note,
                   c.nome AS cliente_nome,
                   ca.nome AS cantiere_nome
            FROM costi co
            LEFT JOIN clienti c ON co.cliente_id = c.id
            LEFT JOIN cantieri ca ON co.cantiere_id = ca.id
            WHERE 1=1
        """
        params: list = []

        if anno:
            query += " AND substr(co.data, 1, 4) = ?"
            params.append(anno)
        if mese and mese != "Tutti":
            query += " AND substr(co.data, 6, 2) = ?"
            params.append(mese)
        if cliente_id is not None:
            query += " AND co.cliente_id = ?"
            params.append(cliente_id)
        if cantiere_id is not None:
            query += " AND co.cantiere_id = ?"
            params.append(cantiere_id)
        if categoria and categoria != "Tutte":
            query += " AND co.categoria = ?"
            params.append(categoria)

        query += " ORDER BY co.data DESC, co.id DESC"
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def get_costo_by_id(costo_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM costi WHERE id = ?", (costo_id,)).fetchone()
        return dict(row) if row else None


def create_costo(
    data: str,
    descrizione: str,
    importo: float,
    categoria: str | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    pagato: bool = True,
    note: str | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO costi (data, descrizione, categoria, importo,
                               cliente_id, cantiere_id, pagato, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data, descrizione, categoria, importo, cliente_id, cantiere_id,
             1 if pagato else 0, note),
        )
        return cursor.lastrowid


def update_costo(
    costo_id: int,
    data: str,
    descrizione: str,
    importo: float,
    categoria: str | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    pagato: bool = True,
    note: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE costi
            SET data = ?, descrizione = ?, categoria = ?, importo = ?,
                cliente_id = ?, cantiere_id = ?, pagato = ?, note = ?
            WHERE id = ?
            """,
            (data, descrizione, categoria, importo, cliente_id, cantiere_id,
             1 if pagato else 0, note, costo_id),
        )


def delete_costo(costo_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM costi WHERE id = ?", (costo_id,))
