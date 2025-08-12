# schemas/parametri.py

from pydantic import BaseModel
from typing import Optional, List


class ParametriDaInserireBase(BaseModel):
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float] = None  
    perc_premio_annuale: Optional[float] = None      
    valore_limite: Optional[int] = None              
    perc_100_budget: Optional[float] = None  
    user_id: Optional[str] = None        


class ParametriDaInserireCreate(ParametriDaInserireBase):
    pass


class ParametriDaInserireRead(ParametriDaInserireBase):
    id: int


class ParametriDaInserireUpdate(BaseModel):
    mese: Optional[str] = None
    obiettivo_mensile: Optional[float] = None
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: Optional[int] = None
    perc_100_budget: Optional[float] = None

class ParametriBulkUpdateItem(BaseModel):
    id: Optional[int]            # If provided → update, else create new
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: float
    perc_100_budget: float

class ParametriBulkUpdate(BaseModel):
    table: List[ParametriBulkUpdateItem]