from database.db import get_connection


def get_cantieri_by_cliente(cliente_id: int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, cliente_id, nome, localita, indirizzo, note
            FROM cantieri
            WHERE cliente_id = ?
            ORDER BY nome ASC
        """, (cliente_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_all_cantieri() -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ca.id, ca.cliente_id, ca.nome, ca.localita, ca.indirizzo, ca.note,
                   c.nome AS cliente_nome
            FROM cantieri ca
            JOIN clienti c ON ca.cliente_id = c.id
            ORDER BY ca.nome ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_cantiere_by_id(cantiere_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, cliente_id, nome, localita, indirizzo, note
            FROM cantieri
            WHERE id = ?
        """, (cantiere_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_cantiere(
    cliente_id: int,
    nome: str,
    localita: str | None = None,
    indirizzo: str | None = None,
    note: str | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cantieri (cliente_id, nome, localita, indirizzo, note)
            VALUES (?, ?, ?, ?, ?)
        """, (cliente_id, nome, localita, indirizzo, note))
        conn.commit()
        return cursor.lastrowid
    

def update_cantiere(
    cantiere_id: int,
    cliente_id: int,
    nome: str,
    localita: str | None = None,
    indirizzo: str | None = None,
    note: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute("""
            UPDATE cantieri
            SET cliente_id = ?, nome = ?, localita = ?, indirizzo = ?, note = ?
            WHERE id = ?
        """, (cliente_id, nome, localita, indirizzo, note, cantiere_id))


def delete_cantiere(cantiere_id: int) -> None:
    """Le fatture e i costi collegati restano, senza cantiere (ON DELETE SET NULL)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM cantieri WHERE id = ?", (cantiere_id,))
