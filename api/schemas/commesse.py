# schemas/icommesse.py

from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import date


class ICommesseBase(BaseModel):
    ordine: Optional[str] = None
    costo: Optional[float] = None   
    ricarico: Optional[float] = None
    data: date
    responsabile: str
    status: int


class ICommesseCreate(ICommesseBase):
    pass


class ICommesseRead(ICommesseBase):
    id: int


class ICommesseUpdate(BaseModel):
    ordine: Optional[str] = None
    data: Optional[date] = None
    responsabile: Optional[str] = None
    status: Optional[int] = None
    costo: Optional[float] = None   
    ricarico: Optional[float] = None
