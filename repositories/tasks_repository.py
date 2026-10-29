from database.db import get_connection


def get_tasks_by_date(task_date: str) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, data, orario, titolo, tag, note, done
            FROM todo_tasks
            WHERE data = ?
            ORDER BY COALESCE(orario, ''), id ASC
            """,
            (task_date,),
        )
        return [dict(row) for row in cursor.fetchall()]


def create_task(data: str, orario: str | None, titolo: str, tag: str | None, note: str | None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO todo_tasks (data, orario, titolo, tag, note, done)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (data, orario, titolo, tag, note),
        )
        conn.commit()
        return cursor.lastrowid


def update_task(task_id: int, data: str, orario: str | None, titolo: str, tag: str | None, note: str | None) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE todo_tasks
            SET data = ?, orario = ?, titolo = ?, tag = ?, note = ?
            WHERE id = ?
            """,
            (data, orario, titolo, tag, note, task_id),
        )
        conn.commit()


def toggle_task_done(task_id: int, done: bool) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE todo_tasks
            SET done = ?
            WHERE id = ?
            """,
            (1 if done else 0, task_id),
        )
        conn.commit()


def delete_task(task_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todo_tasks WHERE id = ?", (task_id,))
        conn.commit()


def get_tasks_in_sospeso(prima_di: str) -> list[dict]:
    """Attività non completate con data precedente a `prima_di` (YYYY-MM-DD)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, data, orario, titolo, tag, note, done
            FROM todo_tasks
            WHERE done = 0 AND data < ?
            ORDER BY data ASC, COALESCE(orario, ''), id ASC
            """,
            (prima_di,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_giorni_con_task(da: str, a: str) -> dict[str, int]:
    """Numero di attività da fare per giorno nell'intervallo (per evidenziare il calendario)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT data, SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS da_fare
            FROM todo_tasks
            WHERE data BETWEEN ? AND ?
            GROUP BY data
            """,
            (da, a),
        )
        return {row["data"]: row["da_fare"] for row in cursor.fetchall()}
