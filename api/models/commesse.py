from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class iCommesse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ordine: str
    data: date
    responsabile: str
    status: int
    costo: float
    ricarico: float