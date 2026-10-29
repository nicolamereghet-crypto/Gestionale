from database.db import get_connection


def get_all_groups() -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome
            FROM customer_groups
            ORDER BY nome ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_group(nome: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_groups (nome)
            VALUES (?)
        """, (nome,))
        conn.commit()
        return cursor.lastrowid

def update_group(group_id: int, nome: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE customer_groups SET nome = ? WHERE id = ?", (nome, group_id))


def delete_group(group_id: int) -> None:
    """I clienti del gruppo restano, senza gruppo (ON DELETE SET NULL)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM customer_groups WHERE id = ?", (group_id,))
