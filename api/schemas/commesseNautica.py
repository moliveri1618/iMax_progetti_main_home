# schemas/icommesse.py

from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import date

class AssignedUser(BaseModel):
    id: int
    name: str


class ICommesseNauticaBase(BaseModel):
    ordine: Optional[str] = None
    costo: Optional[float] = None   
    ricarico: Optional[float] = None
    data: date
    responsabile: str
    status: int
    nome_cliente: Optional[str] = None
    address_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    assignedUserIds: Optional[List[int]] = None


class ICommesseNauticaCreate(ICommesseNauticaBase):
    pass


class ICommesseNauticaRead(ICommesseNauticaBase):
    id: int
    assignedUsers: Optional[List[AssignedUser]] = None


class ICommesseNauticaUpdate(BaseModel):
    ordine: Optional[str] = None
    data: Optional[date] = None
    responsabile: Optional[str] = None
    status: Optional[int] = None
    costo: Optional[float] = None   
    ricarico: Optional[float] = None
    assignedUserIds: Optional[List[int]] = None
