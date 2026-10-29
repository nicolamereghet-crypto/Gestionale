STATI_FATTURA = ["Pagato", "Pendente", "Non pagato"]
STATI_APERTI = ("Pendente", "Non pagato")

CATEGORIE_COSTO = [
    "Materiali",
    "Manodopera",
    "Subappalti",
    "Noleggi",
    "Carburante",
    "Spese generali",
    "Altro",
]


def validate_nome(nome: str, field_name: str = "Nome") -> str:
    cleaned = (nome or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} obbligatorio.")
    if len(cleaned) < 2:
        raise ValueError(f"{field_name} troppo breve.")
    return cleaned


def validate_importo(importo: float) -> float:
    try:
        importo = float(importo)
    except (TypeError, ValueError) as exc:
        raise ValueError("Importo non valido.") from exc
    if importo < 0:
        raise ValueError("L'importo non può essere negativo.")
    return round(importo, 2)


def validate_stato(stato: str) -> str:
    if stato not in STATI_FATTURA:
        raise ValueError(f"Stato non valido: {stato}")
    return stato
