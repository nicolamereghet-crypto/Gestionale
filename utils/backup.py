import sqlite3
from datetime import datetime
from pathlib import Path

from utils.paths import backup_dir as _default_backup_dir


def backup_database(db_path: str, backup_dir: str | Path | None = None, max_backups: int = 30) -> Path | None:
    """
    Crea una copia del database SQLite con timestamp.
    Mantiene solo gli ultimi N backup.

    Usa l'API di backup di SQLite invece di copiare il file: la copia
    resta coerente anche se il database è in uso.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print("Database non trovato, backup saltato")
        return None

    backup_dir = Path(backup_dir) if backup_dir else _default_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"gestionale_backup_{timestamp}.db"

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        print(f"Backup creato: {backup_path}")
    except Exception as e:
        print(f"Errore backup: {e}")
        return None

    files = sorted(backup_dir.glob("gestionale_backup_*.db"), reverse=True)
    for old_file in files[max_backups:]:
        try:
            old_file.unlink()
        except Exception:
            pass

    return backup_path
