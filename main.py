import logging
import os
import sys
import tempfile
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from utils.paths import SOURCE_DIR, log_path
from version import APP_NAME, __version__

logging.basicConfig(
    filename=str(log_path()),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("gestionale")


def _install_error_handler() -> None:
    """Nel .exe non c'è un terminale: ogni errore imprevisto viene scritto nel
    file di log e mostrato in una finestra, invece di chiudere l'app in silenzio."""

    def handler(exc_type, exc, tb):
        testo = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("Errore non gestito:\n%s", testo)
        try:
            QMessageBox.critical(
                None,
                "Si è verificato un errore",
                f"{exc}\n\nI dettagli sono stati salvati in:\n{log_path()}\n\n"
                "Manda questo file a chi ti assiste.",
            )
        except Exception:
            pass

    sys.excepthook = handler


def _primo_avvio(db_path, import_database) -> None:
    """Se non esiste ancora un database, propone di importare quello in uso finora."""
    risposta = QMessageBox.question(
        None,
        f"Benvenuto in {APP_NAME}",
        "È il primo avvio su questo computer.\n\n"
        "Hai già un file del gestionale con i tuoi dati (gestionale.db) da importare?\n\n"
        "• Sì: scegli il file e ritrovi tutte le fatture.\n"
        "• No: si parte con un gestionale vuoto.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if risposta != QMessageBox.StandardButton.Yes:
        return
    while True:
        path, _ = QFileDialog.getOpenFileName(
            None, "Scegli il file del gestionale", os.path.expanduser("~"), "Database (*.db);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            import_database(path)
            QMessageBox.information(None, APP_NAME, "Dati importati correttamente.")
            log.info("Database importato da %s", path)
            return
        except Exception as exc:
            QMessageBox.warning(None, APP_NAME, f"{exc}\nScegli un altro file.")


def main() -> int:
    selftest = "--selftest" in sys.argv
    if selftest:
        # prova automatica (usata da GitHub Actions): database temporaneo, nessuna finestra di dialogo
        os.environ["GESTIONALE_DATA_DIR"] = tempfile.mkdtemp(prefix="gestionale_test_")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")  # aspetto identico su Mac e Windows, sempre chiaro
    icona = SOURCE_DIR / "assets" / "icon.png"
    if icona.exists():
        app.setWindowIcon(QIcon(str(icona)))

    # import dopo aver eventualmente impostato GESTIONALE_DATA_DIR
    from database.db import DB_PATH, import_database, init_db, migrate_legacy_location, seed_basic_data
    from ui.main_window import MainWindow
    from ui.theme import APP_STYLE, light_palette
    from utils.backup import backup_database

    app.setPalette(light_palette())
    app.setStyleSheet(APP_STYLE)

    if not selftest:
        _install_error_handler()
        log.info("Avvio %s %s - database: %s", APP_NAME, __version__, DB_PATH)
        if migrate_legacy_location():
            log.info("Database copiato dalla vecchia cartella data/")
        if not DB_PATH.exists():
            _primo_avvio(DB_PATH, import_database)

    # Prima il backup, poi eventuali migrazioni: se qualcosa va storto
    # c'è sempre la copia del database com'era prima dell'aggiornamento.
    backup_database(str(DB_PATH))
    init_db()
    seed_basic_data()

    window = MainWindow()
    window.setWindowTitle(f"{APP_NAME} {__version__}")

    if selftest:
        for key in window.pages:
            window.show_page(key)
        app.processEvents()
        print(f"SELFTEST OK - {APP_NAME} {__version__}")
        return 0

    window.show()
    return app.exec()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        # in prova automatica un errore deve dare codice d'uscita 1, non una finestra
        try:
            sys.exit(main())
        except Exception:
            traceback.print_exc()
            log.error("SELFTEST FALLITO:\n%s", traceback.format_exc())
            sys.exit(1)
    sys.exit(main())
