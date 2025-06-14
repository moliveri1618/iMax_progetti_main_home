from pydantic import BaseModel
from typing import Optional
from datetime import date
from sqlmodel import SQLModel
from typing import List

class IWorkInProgressBase(BaseModel):
    commesse_id: int
    zona: str
    modello: str
    colonna: str
    completato: bool
    completato_da_user: str
    data_completamento: Optional[date] = None


class IWorkInProgressCreate(IWorkInProgressBase):
    pass


class IWorkInProgressRead(SQLModel):
    id: int
    commesse_id: int
    zona: str
    modello: str
    colonna: str
    completato: bool
    completato_da_user: str
    data_completamento: Optional[date]

    class Config:
        from_attributes = True  # required for SQLModel with Pydantic v2+


class IWorkInProgressUpdate(BaseModel):
    commesse_id: Optional[int] = None
    zona: Optional[str] = None
    modello: Optional[str] = None
    colonna: Optional[str] = None
    completato: Optional[bool] = None
    completato_da_user: Optional[str] = None
    data_completamento: Optional[date] = None

class WorkInProgressGrouped(SQLModel):
    zona: str
    modello: str
    steps: List[IWorkInProgressRead]