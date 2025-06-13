from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class iCommesse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ordine: str
    data: Optional[date] = None
    responsabile: Optional[str] = None
    status: Optional[int] = None
    costo: Optional[float] = None
    ricarico: Optional[float] = None
    nome_cliente: Optional[str] = None
    address_cliente: Optional[str] = None
    email_cliente: Optional[str] = None