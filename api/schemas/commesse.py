# schemas/icommesse.py

from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import date


class ICommesseBase(BaseModel):
    nome_cliente: str
    indirizzo: str
    riferimento_cliente: str
    ordine_n: int
    data: date
    responsabile: str
    email: str
    status: int
    report_tecnico: str
    report_cliente: str


class ICommesseCreate(ICommesseBase):
    pass


class ICommesseRead(ICommesseBase):
    id: int


class ICommesseUpdate(BaseModel):
    nome_cliente: Optional[str] = None
    indirizzo: Optional[str] = None
    riferimento_cliente: Optional[str] = None
    ordine_n: Optional[int] = None
    data: Optional[date] = None
    responsabile: Optional[str] = None
    email: Optional[str] = None
    status: Optional[int] = None
    report_tecnico: Optional[str] = None
    report_cliente: Optional[str] = None
