from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, ARRAY, Integer
from datetime import date, datetime


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
    assignedUserIds: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(ARRAY(Integer), nullable=True),
    )
    costo_ok: Optional[bool] = None
    data_costo_ok: Optional[datetime] = None
