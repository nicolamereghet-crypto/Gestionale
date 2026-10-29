from repositories.fatture_repository import (
    create_fattura,
    update_fattura,
    get_fattura_by_id,
    update_fattura_status,
    delete_fattura,
)
from repositories.storico_repository import create_storico
from utils.date_utils import today_str, now_str, normalize_date
from utils.validators import validate_importo, validate_stato

# Valore "non passato": serve a distinguere "lascia la scadenza com'è"
# (la vecchia interfaccia non conosce il campo) da "togli la scadenza" (None).
_INVARIATA = object()


def _normalizza_date(
    stato: str,
    data_inserimento: str | None,
    data_scadenza: str | None,
    data_estinzione: str | None,
) -> tuple[str, str | None, str | None]:
    data_inserimento = normalize_date(data_inserimento) or today_str()
    data_scadenza = normalize_date(data_scadenza)
    data_estinzione = normalize_date(data_estinzione)

    if data_scadenza and data_scadenza < data_inserimento:
        raise ValueError("La scadenza non può essere precedente alla data della fattura.")

    if stato == "Pagato" and not data_estinzione:
        data_estinzione = today_str()
    if stato != "Pagato":
        data_estinzione = None

    return data_inserimento, data_scadenza, data_estinzione


def create_fattura_service(
    cliente_id: int,
    cantiere_id: int | None,
    numero_fattura: str | None,
    importo: float,
    stato: str,
    data_inserimento: str,
    data_estinzione: str | None = None,
    note: str | None = None,
    data_scadenza: str | None = None,
) -> int:
    importo = validate_importo(importo)
    stato = validate_stato(stato)
    data_inserimento, data_scadenza, data_estinzione = _normalizza_date(
        stato, data_inserimento, data_scadenza, data_estinzione
    )

    fattura_id = create_fattura(
        cliente_id=cliente_id,
        cantiere_id=cantiere_id,
        numero_fattura=numero_fattura,
        importo=importo,
        stato=stato,
        data_inserimento=data_inserimento,
        data_estinzione=data_estinzione,
        note=note,
        data_scadenza=data_scadenza,
    )

    create_storico(
        fattura_id=fattura_id,
        azione="CREAZIONE_FATTURA",
        dettagli=f"Creata fattura n. {numero_fattura or '-'} (ID={fattura_id}), importo {importo:.2f} €",
        data_evento=now_str(),
    )

    return fattura_id


def update_fattura_service(
    fattura_id: int,
    cliente_id: int,
    cantiere_id: int | None,
    numero_fattura: str | None,
    importo: float,
    stato: str,
    data_inserimento: str,
    data_estinzione: str | None = None,
    note: str | None = None,
    data_scadenza=_INVARIATA,
) -> None:
    vecchia = get_fattura_by_id(fattura_id)
    if not vecchia:
        raise ValueError("Fattura non trovata.")

    if data_scadenza is _INVARIATA:
        data_scadenza = vecchia.get("data_scadenza")

    importo = validate_importo(importo)
    stato = validate_stato(stato)
    data_inserimento, data_scadenza, data_estinzione = _normalizza_date(
        stato, data_inserimento, data_scadenza, data_estinzione
    )

    update_fattura(
        fattura_id=fattura_id,
        cliente_id=cliente_id,
        cantiere_id=cantiere_id,
        numero_fattura=numero_fattura,
        importo=importo,
        stato=stato,
        data_inserimento=data_inserimento,
        data_estinzione=data_estinzione,
        note=note,
        data_scadenza=data_scadenza,
    )

    modifiche = []
    if float(vecchia["importo"]) != importo:
        modifiche.append(f"importo {float(vecchia['importo']):.2f} → {importo:.2f} €")
    if vecchia["stato"] != stato:
        modifiche.append(f"stato '{vecchia['stato']}' → '{stato}'")
    if vecchia.get("data_scadenza") != data_scadenza:
        modifiche.append(f"scadenza {vecchia.get('data_scadenza') or '-'} → {data_scadenza or '-'}")

    create_storico(
        fattura_id=fattura_id,
        azione="MODIFICA_FATTURA",
        dettagli=f"Modificata fattura ID={fattura_id}"
        + (": " + ", ".join(modifiche) if modifiche else ""),
        data_evento=now_str(),
    )


def update_fattura_status_service(
    fattura_id: int,
    nuovo_stato: str,
    data_estinzione: str | None = None,
) -> None:
    fattura = get_fattura_by_id(fattura_id)
    if not fattura:
        raise ValueError("Fattura non trovata.")

    stato_precedente = fattura["stato"]
    nuovo_stato = validate_stato(nuovo_stato)
    data_estinzione = normalize_date(data_estinzione)

    if nuovo_stato == "Pagato" and not data_estinzione:
        # se era già pagata mantieni la data originale, altrimenti oggi
        data_estinzione = fattura.get("data_estinzione") or today_str()

    if nuovo_stato != "Pagato":
        data_estinzione = None

    update_fattura_status(
        fattura_id=fattura_id,
        nuovo_stato=nuovo_stato,
        data_estinzione=data_estinzione,
    )

    create_storico(
        fattura_id=fattura_id,
        azione="MODIFICA_STATO",
        dettagli=f"Fattura ID={fattura_id}: stato da '{stato_precedente}' a '{nuovo_stato}'",
        data_evento=now_str(),
    )


def delete_fattura_service(fattura_id: int) -> None:
    fattura = get_fattura_by_id(fattura_id)
    if not fattura:
        raise ValueError("Fattura non trovata.")

    dettagli = (
        f"Eliminata fattura ID={fattura_id}, "
        f"cliente_id={fattura['cliente_id']}, "
        f"importo={fattura['importo']:.2f}, "
        f"stato='{fattura['stato']}', "
        f"numero='{fattura.get('numero_fattura') or ''}'"
    )

    delete_fattura(fattura_id)

    create_storico(
        fattura_id=None,
        azione="ELIMINAZIONE_FATTURA",
        dettagli=dettagli,
        data_evento=now_str(),
    )
