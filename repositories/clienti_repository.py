from database.db import get_connection


def get_all_clienti(group_id: int | None = None) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT c.id, c.nome, c.group_id, c.email, c.telefono, c.note,
                   g.nome AS gruppo_nome
            FROM clienti c
            LEFT JOIN customer_groups g ON c.group_id = g.id
            WHERE 1=1
        """
        params = []

        if group_id is not None:
            query += " AND c.group_id = ?"
            params.append(group_id)

        query += " ORDER BY c.nome ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_cliente_by_id(cliente_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome, group_id, email, telefono, note
            FROM clienti
            WHERE id = ?
        """, (cliente_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_cliente(
    nome: str,
    group_id: int | None,
    email: str | None = None,
    telefono: str | None = None,
    note: str | None = None,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clienti (nome, group_id, email, telefono, note)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, group_id, email, telefono, note))
        conn.commit()
        return cursor.lastrowid


def update_cliente(
    cliente_id: int,
    nome: str,
    group_id: int | None,
    email: str | None = None,
    telefono: str | None = None,
    note: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute("""
            UPDATE clienti
            SET nome = ?, group_id = ?, email = ?, telefono = ?, note = ?
            WHERE id = ?
        """, (nome, group_id, email, telefono, note, cliente_id))


def count_fatture_cliente(cliente_id: int) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM fatture WHERE cliente_id = ?", (cliente_id,)
        ).fetchone()[0]


def delete_cliente(cliente_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM clienti WHERE id = ?", (cliente_id,))
