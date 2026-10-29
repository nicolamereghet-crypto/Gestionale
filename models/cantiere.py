from dataclasses import dataclass
from typing import Optional


@dataclass
class Cantiere:
    id: Optional[int]
    cliente_id: int
    nome: str
    localita: Optional[str] = None
    indirizzo: Optional[str] = None
    note: Optional[str] = None