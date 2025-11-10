# schemas/iParametriTecnici.py
from typing import Optional
from sqlmodel import SQLModel

class IParametriTecniciBase(SQLModel):
    piano_gru_0_1: Optional[float] = None
    piano_2_3: Optional[float] = None
    piano_4_5: Optional[float] = None
    piano_6_7: Optional[float] = None
    report_tecnico_tickets: Optional[str] = None
    report_tecnico_pv: Optional[str] = None

class IParametriTecniciCreate(IParametriTecniciBase):
    pass

class IParametriTecniciRead(IParametriTecniciBase):
    id: int

class IParametriTecniciUpdate(SQLModel):
    piano_gru_0_1: Optional[float] = None
    piano_2_3: Optional[float] = None
    piano_4_5: Optional[float] = None
    piano_6_7: Optional[float] = None
    report_tecnico_tickets: Optional[str] = None
    report_tecnico_pv: Optional[str] = None

# For convenience: allow upsert by optional id
class IParametriTecniciUpsert(IParametriTecniciBase):
    id: Optional[int] = None
