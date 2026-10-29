from dataclasses import dataclass
from typing import Optional


@dataclass
class GruppoCliente:
    id: Optional[int]
    nome: str