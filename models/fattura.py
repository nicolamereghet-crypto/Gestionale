from dataclasses import dataclass
from typing import Optional


@dataclass
class Fattura:
    id: Optional[int]
    cliente_id: int
    cantiere_id: Optional[int]
    numero_fattura: Optional[str]
    importo: float
    stato: str
    data_inserimento: str
    data_scadenza: Optional[str] = None
    data_estinzione: Optional[str] = None
    note: Optional[str] = None