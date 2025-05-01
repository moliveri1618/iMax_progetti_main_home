from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class iCommesse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
