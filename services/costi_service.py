from repositories.cantieri_repository import get_cantiere_by_id
from repositories.costi_repository import (
    create_costo,
    delete_costo,
    get_costo_by_id,
    update_costo,
)
from repositories.storico_repository import create_storico
from utils.date_utils import normalize_date, now_str, today_str
from utils.validators import validate_importo, validate_nome


def _prepara(data, descrizione, importo, cliente_id, cantiere_id):
    data = normalize_date(data) or today_str()
    descrizione = validate_nome(descrizione, "Descrizione")
    importo = validate_importo(importo)

    # Se il costo è legato a un cantiere, il cliente è quello del cantiere
    if cantiere_id is not None:
        cantiere = get_cantiere_by_id(cantiere_id)
        if not cantiere:
            raise ValueError("Cantiere non trovato.")
        if cliente_id is not None and cliente_id != cantiere["cliente_id"]:
            raise ValueError("Il cantiere selezionato non appartiene a questo cliente.")
        cliente_id = cantiere["cliente_id"]

    return data, descrizione, importo, cliente_id, cantiere_id


def create_costo_service(
    data: str | None,
    descrizione: str,
    importo: float,
    categoria: str | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    pagato: bool = True,
    note: str | None = None,
) -> int:
    data, descrizione, importo, cliente_id, cantiere_id = _prepara(
        data, descrizione, importo, cliente_id, cantiere_id
    )
    costo_id = create_costo(data, descrizione, importo, categoria,
                            cliente_id, cantiere_id, pagato, note)
    create_storico(
        fattura_id=None,
        azione="CREAZIONE_COSTO",
        dettagli=f"Creato costo ID={costo_id}: {descrizione}, {importo:.2f} €",
        data_evento=now_str(),
    )
    return costo_id


def update_costo_service(
    costo_id: int,
    data: str | None,
    descrizione: str,
    importo: float,
    categoria: str | None = None,
    cliente_id: int | None = None,
    cantiere_id: int | None = None,
    pagato: bool = True,
    note: str | None = None,
) -> None:
    if not get_costo_by_id(costo_id):
        raise ValueError("Costo non trovato.")
    data, descrizione, importo, cliente_id, cantiere_id = _prepara(
        data, descrizione, importo, cliente_id, cantiere_id
    )
    update_costo(costo_id, data, descrizione, importo, categoria,
                 cliente_id, cantiere_id, pagato, note)
    create_storico(
        fattura_id=None,
        azione="MODIFICA_COSTO",
        dettagli=f"Modificato costo ID={costo_id}: {descrizione}, {importo:.2f} €",
        data_evento=now_str(),
    )


def delete_costo_service(costo_id: int) -> None:
    costo = get_costo_by_id(costo_id)
    if not costo:
        raise ValueError("Costo non trovato.")
    delete_costo(costo_id)
    create_storico(
        fattura_id=None,
        azione="ELIMINAZIONE_COSTO",
        dettagli=f"Eliminato costo ID={costo_id}: {costo['descrizione']}, {costo['importo']:.2f} €",
        data_evento=now_str(),
    )
