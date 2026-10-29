import sqlite3
from pathlib import Path

from utils.paths import LEGACY_DB_PATH, data_dir

DATA_DIR = data_dir()
DB_PATH = DATA_DIR / "gestionale.db"

# Versione dello schema: aumentala quando aggiungi una nuova migrazione in _migrate()
SCHEMA_VERSION = 2

GRUPPI_INIZIALI = ["Brescia", "Borgosatollo"]


class _ClosingConnection(sqlite3.Connection):
    """Connessione che, usata con `with`, fa commit/rollback E si chiude.

    La sqlite3.Connection standard con `with` fa solo commit/rollback ma
    lascia la connessione aperta: in un'app che resta accesa a lungo
    (come la futura versione web) le connessioni si accumulerebbero.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=_ClosingConnection, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cursor.fetchall()}


def _create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            group_id INTEGER,
            email TEXT,
            telefono TEXT,
            note TEXT,
            FOREIGN KEY (group_id) REFERENCES customer_groups(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cantieri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            localita TEXT,
            indirizzo TEXT,
            note TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fatture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            cantiere_id INTEGER,
            numero_fattura TEXT,
            importo REAL NOT NULL DEFAULT 0,
            stato TEXT NOT NULL DEFAULT 'Pendente',
            data_inserimento TEXT NOT NULL,
            data_scadenza TEXT,
            data_estinzione TEXT,
            note TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY (cantiere_id) REFERENCES cantieri(id) ON DELETE SET NULL
        )
    """)

    # ON DELETE SET NULL: eliminando una fattura il suo storico resta consultabile
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fattura_id INTEGER,
            azione TEXT NOT NULL,
            dettagli TEXT,
            data_evento TEXT NOT NULL,
            FOREIGN KEY (fattura_id) REFERENCES fatture(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todo_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            orario TEXT,
            titolo TEXT NOT NULL,
            tag TEXT,
            note TEXT,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Costi: collegabili a un cantiere e/o cliente, oppure generali (entrambi NULL)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS costi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            descrizione TEXT NOT NULL,
            categoria TEXT,
            importo REAL NOT NULL DEFAULT 0,
            cliente_id INTEGER,
            cantiere_id INTEGER,
            pagato INTEGER NOT NULL DEFAULT 1,
            note TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id) ON DELETE SET NULL,
            FOREIGN KEY (cantiere_id) REFERENCES cantieri(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fatture_data ON fatture(data_inserimento)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fatture_stato ON fatture(stato)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_costi_data ON costi(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_data ON todo_tasks(data)")


def _migrate(conn: sqlite3.Connection) -> None:
    """Porta un database esistente all'ultima versione senza perdere dati."""
    cursor = conn.cursor()
    version = cursor.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return

    # 1) Nuova colonna data_scadenza sulle fatture
    if "data_scadenza" not in _column_names(cursor, "fatture"):
        cursor.execute("ALTER TABLE fatture ADD COLUMN data_scadenza TEXT")

    # 2) Storico: da ON DELETE CASCADE a ON DELETE SET NULL
    #    (SQLite non permette di cambiare una foreign key: si ricrea la tabella)
    cursor.execute("PRAGMA foreign_key_list(storico)")
    fk = [row for row in cursor.fetchall() if row["table"] == "fatture"]
    if fk and fk[0]["on_delete"].upper() == "CASCADE":
        conn.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("ALTER TABLE storico RENAME TO storico_old")
        cursor.execute("""
            CREATE TABLE storico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fattura_id INTEGER,
                azione TEXT NOT NULL,
                dettagli TEXT,
                data_evento TEXT NOT NULL,
                FOREIGN KEY (fattura_id) REFERENCES fatture(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("""
            INSERT INTO storico (id, fattura_id, azione, dettagli, data_evento)
            SELECT id, fattura_id, azione, dettagli, data_evento FROM storico_old
        """)
        cursor.execute("DROP TABLE storico_old")
        conn.execute("PRAGMA foreign_keys = ON")

    cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def init_db() -> None:
    with get_connection() as conn:
        _create_tables(conn.cursor())
        _migrate(conn)


def seed_basic_data() -> None:
    """Crea i gruppi iniziali solo al primo avvio (tabella vuota).

    Così se il cliente rinomina o elimina un gruppo, non ricompare
    al riavvio successivo.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        count = cursor.execute("SELECT COUNT(*) FROM customer_groups").fetchone()[0]
        if count:
            return
        for nome in GRUPPI_INIZIALI:
            cursor.execute(
                "INSERT OR IGNORE INTO customer_groups (nome) VALUES (?)", (nome,)
            )


def _ro_uri(path) -> str:
    """URI SQLite in sola lettura (funziona anche con spazi e percorsi Windows)."""
    return f"{Path(path).resolve().as_uri()}?mode=ro"


def is_valid_database(path) -> bool:
    """True se il file è un database del gestionale (contiene la tabella fatture)."""
    try:
        conn = sqlite3.connect(_ro_uri(path), uri=True)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fatture'"
            ).fetchone()
            return row is not None
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def import_database(source) -> None:
    """Copia un database esistente nella posizione usata dall'app."""
    if not is_valid_database(source):
        raise ValueError("Il file scelto non è un database del gestionale.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(_ro_uri(source), uri=True)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def migrate_legacy_location() -> bool:
    """Se il database esiste solo nella vecchia cartella `data/` del progetto,
    lo copia nella nuova posizione (l'originale resta dov'è). True se copiato."""
    if DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return False
    if not is_valid_database(LEGACY_DB_PATH):
        return False
    import_database(LEGACY_DB_PATH)
    return True
