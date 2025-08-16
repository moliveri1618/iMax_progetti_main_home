# schemas/parametri.py

from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import SQLModel, Field, Session, select


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


class ParametriDaInserireRead(SQLModel):
    id: int
    user_id: str
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float]
    perc_premio_annuale: Optional[float]
    valore_limite: Optional[int]
    perc_100_budget: Optional[float]

class ParametriDaInserireUpsert(SQLModel):
    id: Optional[int] = None
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: Optional[int] = None
    perc_100_budget: Optional[float] = None


class ParametriDaInserireUpdate(BaseModel):
    mese: Optional[str] = None
    obiettivo_mensile: Optional[float] = None
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: Optional[int] = None
    perc_100_budget: Optional[float] = None

class ParametriBulkUpdateItem(BaseModel):
    id: Optional[int]           
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: float
    perc_100_budget: float
    
class ParametriRowIn(SQLModel):
    mese: str
    obiettivo_mensile: float
    perc_premio_trimestrale: Optional[float] = None
    perc_premio_annuale: Optional[float] = None
    valore_limite: Optional[int] = None
    perc_100_budget: Optional[float] = None
    

class ParametriBulkUpdate(BaseModel):
    table: List[ParametriBulkUpdateItem]
    
    
TEMPLATE_ROWS = [
    {"mese": "gennaio",   "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": 0.14, "valore_limite": 140, "perc_100_budget": 1700},
    {"mese": "febbraio",  "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 999, "perc_100_budget": 8},
    {"mese": "marzo",     "obiettivo_mensile": 1000, "perc_premio_trimestrale": 0.5,  "perc_premio_annuale": None, "valore_limite": 110, "perc_100_budget": 5},
    {"mese": "aprile",    "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 100, "perc_100_budget": 3.5},
    {"mese": "maggio",    "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 95,  "perc_100_budget": 3},
    {"mese": "giugno",    "obiettivo_mensile": 1000, "perc_premio_trimestrale": 0.5,  "perc_premio_annuale": None, "valore_limite": 90,  "perc_100_budget": 2.5},
    {"mese": "luglio",    "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 85,  "perc_100_budget": 2},
    {"mese": "agosto",    "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 80,  "perc_100_budget": 1.5},
    {"mese": "settembre", "obiettivo_mensile": 1000, "perc_premio_trimestrale": 0.5,  "perc_premio_annuale": None, "valore_limite": 75,  "perc_100_budget": 1},
    {"mese": "ottobre",   "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 70,  "perc_100_budget": 0.5},
    {"mese": "novembre",  "obiettivo_mensile": 1000, "perc_premio_trimestrale": None, "perc_premio_annuale": None, "valore_limite": 65,  "perc_100_budget": -1},
    {"mese": "dicembre",  "obiettivo_mensile": 1000, "perc_premio_trimestrale": 0.5,  "perc_premio_annuale": None, "valore_limite": 60,  "perc_100_budget": -3},
]

###########################
#### TEST FROM FASTAPI ####
###########################
'''
[
  {"mese":"gennaio","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":0.14,"valore_limite":140,"perc_100_budget":1700},
  {"mese":"febbraio","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":999,"perc_100_budget":8},
  {"mese":"marzo","obiettivo_mensile":1000,"perc_premio_trimestrale":0.5,"perc_premio_annuale":null,"valore_limite":110,"perc_100_budget":5},
  {"mese":"aprile","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":100,"perc_100_budget":3.5},
  {"mese":"maggio","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":95,"perc_100_budget":3},
  {"mese":"giugno","obiettivo_mensile":1000,"perc_premio_trimestrale":0.5,"perc_premio_annuale":null,"valore_limite":90,"perc_100_budget":2.5},
  {"mese":"luglio","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":85,"perc_100_budget":2},
  {"mese":"agosto","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":80,"perc_100_budget":1.5},
  {"mese":"settembre","obiettivo_mensile":1000,"perc_premio_trimestrale":0.5,"perc_premio_annuale":null,"valore_limite":75,"perc_100_budget":1},
  {"mese":"ottobre","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":70,"perc_100_budget":0.5},
  {"mese":"novembre","obiettivo_mensile":1000,"perc_premio_trimestrale":null,"perc_premio_annuale":null,"valore_limite":65,"perc_100_budget":-1},
  {"mese":"dicembre","obiettivo_mensile":1000,"perc_premio_trimestrale":0.5,"perc_premio_annuale":null,"valore_limite":60,"perc_100_budget":-3}
]
'''



MONTHS = {r["mese"] for r in TEMPLATE_ROWS}
MONTH_ORDER = {m: i for i, m in enumerate([r["mese"] for r in TEMPLATE_ROWS])}