from sqlmodel import SQLModel, Field
from typing import Optional

class ParametriDaInserire(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mese: str = Field(index=True)  
    obiettivo_mensile: float = Field(default=0.0)  
    perc_premio_trimestrale: Optional[float] = Field(default=None)  
    perc_premio_annuale: Optional[float] = Field(default=None) 
    valore_limite: Optional[int] = Field(default=None)  
    perc_100_budget: Optional[float] = Field(default=None)  
