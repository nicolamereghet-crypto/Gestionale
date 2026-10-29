from dataclasses import dataclass
from typing import Optional


@dataclass
class Costo:
    id: Optional[int]
    data: str
    descrizione: str
    importo: float
    categoria: Optional[str] = None
    cliente_id: Optional[int] = None
    cantiere_id: Optional[int] = None
    pagato: bool = True
    note: Optional[str] = None
