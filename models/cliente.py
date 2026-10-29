from dataclasses import dataclass
from typing import Optional


@dataclass
class Cliente:
    id: Optional[int]
    nome: str
    group_id: Optional[int]
    email: Optional[str] = None
    telefono: Optional[str] = None
    note: Optional[str] = None