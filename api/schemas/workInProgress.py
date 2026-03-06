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
    assigned_users_ids: Optional[List[int]] = None
    valore: Optional[float] = None  


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
    assigned_users_ids: Optional[List[int]] = None
    valore: Optional[float] = None  
    percentuale_completamento_collaudo_finale: Optional[float] = None

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
    assigned_users_ids: Optional[List[int]] = None
    valore: Optional[float] = None

class WorkInProgressGrouped(SQLModel):
    zona: str
    modello: str
    steps: List[IWorkInProgressRead]
    
    
    
class ICollaudoFinaleRead(SQLModel):
    id: int
    workInProgress_id: Optional[int] = None
    rilievo_misure: Optional[float] = None
    collaudo_sarte: Optional[float] = None
    taglio_binario: Optional[float] = None
    image_paths_RM: Optional[List[str]] = []
    image_paths_CS: Optional[List[str]] = []
    image_paths_TB: Optional[List[str]] = []

    class Config:
        from_attributes = True


class IWorkInProgressWithCollaudo(IWorkInProgressRead):
    collaudo_finale: Optional[ICollaudoFinaleRead] = None


class WorkInProgressGroupedV2(BaseModel):
    zona: str
    modello: str
    steps: List[IWorkInProgressWithCollaudo]
    
    
class WorkInProgressTabLavori(IWorkInProgressRead):
    ordine: str | None = None
    data: date | None = None
    nome_cliente: str | None = None