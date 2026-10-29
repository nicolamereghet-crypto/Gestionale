"""Dove l'applicazione salva i suoi file.

Il database NON sta nella cartella del programma: così installare una nuova
versione (o disinstallare) non tocca mai i dati del cliente.

  Windows
    database: %LOCALAPPDATA%\\Gestionale\\gestionale.db   (non sincronizzato con OneDrive)
    backup:   Documenti\\Gestionale - Backup\\              (se Documenti è su OneDrive, i backup finiscono anche nel cloud)
  macOS
    database: ~/Library/Application Support/Gestionale/gestionale.db
    backup:   ~/Documents/Gestionale - Backup/

Per test o casi particolari si può forzare una cartella con la variabile
d'ambiente GESTIONALE_DATA_DIR (database e backup finiscono lì dentro).
"""
import os
import sys
from pathlib import Path

APP_DIR_NAME = "Gestionale"
BACKUP_DIR_NAME = "Gestionale - Backup"

# Cartella del codice sorgente (o, nel .exe, cartella temporanea di PyInstaller)
SOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
# Vecchia posizione del database (versioni precedenti, avviate da sorgente)
LEGACY_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gestionale.db"


def _windows_documents() -> Path | None:
    """Percorso reale di Documenti su Windows (anche se spostato su OneDrive)."""
    try:
        import ctypes
        from ctypes import wintypes

        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5 (Documenti), SHGFP_TYPE_CURRENT = 0
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return Path(buf.value)
    except Exception:
        pass
    return None


def data_dir() -> Path:
    override = os.environ.get("GESTIONALE_DATA_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_dir() -> Path:
    override = os.environ.get("GESTIONALE_DATA_DIR")
    if override:
        path = Path(override) / "backup"
    else:
        documenti = _windows_documents() if sys.platform == "win32" else None
        if documenti is None:
            documenti = Path.home() / "Documents"
        path = documenti / BACKUP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return data_dir() / "gestionale.log"
