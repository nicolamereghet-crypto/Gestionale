"""Modifica ed eliminazione di clienti, cantieri e gruppi, con i controlli di sicurezza."""
import sqlite3

from repositories.cantieri_repository import (
    create_cantiere,
    delete_cantiere,
    get_cantiere_by_id,
    update_cantiere,
)
from repositories.clienti_repository import (
    count_fatture_cliente,
    create_cliente,
    delete_cliente,
    get_cliente_by_id,
    update_cliente,
)
from repositories.group_repository import create_group, delete_group, update_group
from repositories.storico_repository import create_storico
from utils.date_utils import now_str
from utils.validators import validate_nome


def _log(azione: str, dettagli: str) -> None:
    create_storico(fattura_id=None, azione=azione, dettagli=dettagli, data_evento=now_str())


# --- Gruppi -------------------------------------------------------------

def create_group_service(nome: str) -> int:
    nome = validate_nome(nome, "Nome gruppo")
    try:
        return create_group(nome)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Esiste già un gruppo chiamato '{nome}'.") from exc


def rename_group_service(group_id: int, nome: str) -> None:
    nome = validate_nome(nome, "Nome gruppo")
    try:
        update_group(group_id, nome)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Esiste già un gruppo chiamato '{nome}'.") from exc
    _log("MODIFICA_GRUPPO", f"Gruppo ID={group_id} rinominato in '{nome}'")


def delete_group_service(group_id: int) -> None:
    delete_group(group_id)
    _log("ELIMINAZIONE_GRUPPO", f"Eliminato gruppo ID={group_id} (i clienti restano senza gruppo)")


# --- Clienti ------------------------------------------------------------

def create_cliente_service(nome, group_id, email=None, telefono=None, note=None) -> int:
    nome = validate_nome(nome, "Nome cliente")
    cliente_id = create_cliente(nome, group_id, email, telefono, note)
    _log("CREAZIONE_CLIENTE", f"Creato cliente ID={cliente_id}: '{nome}'")
    return cliente_id


def update_cliente_service(cliente_id, nome, group_id, email=None, telefono=None, note=None) -> None:
    if not get_cliente_by_id(cliente_id):
        raise ValueError("Cliente non trovato.")
    nome = validate_nome(nome, "Nome cliente")
    update_cliente(cliente_id, nome, group_id, email, telefono, note)
    _log("MODIFICA_CLIENTE", f"Modificato cliente ID={cliente_id}: '{nome}'")


def delete_cliente_service(cliente_id: int) -> None:
    """Rifiuta l'eliminazione se il cliente ha fatture: altrimenti
    il database le cancellerebbe tutte a cascata."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        raise ValueError("Cliente non trovato.")
    n = count_fatture_cliente(cliente_id)
    if n:
        raise ValueError(
            f"Il cliente '{cliente['nome']}' ha {n} fatture: eliminale o spostale prima di eliminare il cliente."
        )
    delete_cliente(cliente_id)
    _log("ELIMINAZIONE_CLIENTE", f"Eliminato cliente ID={cliente_id}: '{cliente['nome']}'")


# --- Cantieri -----------------------------------------------------------

def create_cantiere_service(cliente_id, nome, localita=None, indirizzo=None, note=None) -> int:
    if cliente_id is None:
        raise ValueError("Scegli il cliente del cantiere.")
    nome = validate_nome(nome, "Nome cantiere")
    cantiere_id = create_cantiere(cliente_id, nome, localita, indirizzo, note)
    _log("CREAZIONE_CANTIERE", f"Creato cantiere ID={cantiere_id}: '{nome}'")
    return cantiere_id


def update_cantiere_service(cantiere_id, cliente_id, nome, localita=None, indirizzo=None, note=None) -> None:
    if cliente_id is None:
        raise ValueError("Scegli il cliente del cantiere.")
    if not get_cantiere_by_id(cantiere_id):
        raise ValueError("Cantiere non trovato.")
    nome = validate_nome(nome, "Nome cantiere")
    update_cantiere(cantiere_id, cliente_id, nome, localita, indirizzo, note)
    _log("MODIFICA_CANTIERE", f"Modificato cantiere ID={cantiere_id}: '{nome}'")


def delete_cantiere_service(cantiere_id: int) -> None:
    cantiere = get_cantiere_by_id(cantiere_id)
    if not cantiere:
        raise ValueError("Cantiere non trovato.")
    delete_cantiere(cantiere_id)
    _log("ELIMINAZIONE_CANTIERE", f"Eliminato cantiere ID={cantiere_id}: '{cantiere['nome']}' (fatture e costi restano)")
