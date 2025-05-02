from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class VenditeImax(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ordine: str
    data: str
    venditore: str
    team: str
    cliente: str
    prodotto: str
    descrizione: str
    quantita: float
    prezzo_unitario: float
    costo_unitario: float
    ricarico: float
    subtotale: float