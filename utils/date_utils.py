from datetime import datetime

_FORMATI_ACCETTATI = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    """Data e ora (prima restituiva solo la data: lo storico perdeva l'orario)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_date(value: str | None) -> str | None:
    """Accetta YYYY-MM-DD oppure il formato italiano GG/MM/AAAA e restituisce YYYY-MM-DD."""
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    for fmt in _FORMATI_ACCETTATI:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError("Data non valida: usa il formato GG/MM/AAAA oppure AAAA-MM-GG.")
