from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import SQLModel


# Base schema — used for Create & Update
class IRilievoBase(BaseModel):
    workInProgress_id: Optional[int] = None
    strada_idonea: Optional[bool] = None
    scala_arrivare_piano: Optional[bool] = None
    ascensore_montacarichi: Optional[bool] = None
    uso_mezzo_vicoli: Optional[bool] = None
    autoscala_tiro_piano: Optional[bool] = None
    spazio_manovra: Optional[bool] = None
    cantiere_nuova_costruzione: Optional[bool] = None
    persone_presenti_scarico: Optional[bool] = None
    numero_persone_scarico: Optional[int] = None
    ztl: Optional[bool] = None
    trasporto_difficile_piedi_m: Optional[float] = None
    note: Optional[str] = None
    piani_gru_0_1: Optional[str] = None
    piani_2_3: Optional[str] = None
    piani_4_5: Optional[str] = None
    piani_6_7: Optional[str] = None
    image_paths: Optional[List[str]] = []


# Create schema — used for insertions
class IRilievoCreate(IRilievoBase):
    pass


# Read schema — used for API responses
class IRilievoRead(SQLModel):
    id: int
    workInProgress_id: Optional[int] = None
    strada_idonea: Optional[bool] = None
    scala_arrivare_piano: Optional[bool] = None
    ascensore_montacarichi: Optional[bool] = None
    uso_mezzo_vicoli: Optional[bool] = None
    autoscala_tiro_piano: Optional[bool] = None
    spazio_manovra: Optional[bool] = None
    cantiere_nuova_costruzione: Optional[bool] = None
    persone_presenti_scarico: Optional[bool] = None
    numero_persone_scarico: Optional[int] = None
    ztl: Optional[bool] = None
    trasporto_difficile_piedi_m: Optional[float] = None
    note: Optional[str] = None
    piani_gru_0_1: Optional[str] = None
    piani_2_3: Optional[str] = None
    piani_4_5: Optional[str] = None
    piani_6_7: Optional[str] = None
    image_paths: Optional[List[str]] = []

    class Config:
        from_attributes = True


# Update schema — for PATCH operations
class IRilievoUpdate(BaseModel):
    workInProgress_id: Optional[int] = None
    strada_idonea: Optional[bool] = None
    scala_arrivare_piano: Optional[bool] = None
    ascensore_montacarichi: Optional[bool] = None
    uso_mezzo_vicoli: Optional[bool] = None
    autoscala_tiro_piano: Optional[bool] = None
    spazio_manovra: Optional[bool] = None
    cantiere_nuova_costruzione: Optional[bool] = None
    persone_presenti_scarico: Optional[bool] = None
    numero_persone_scarico: Optional[int] = None
    ztl: Optional[bool] = None
    trasporto_difficile_piedi_m: Optional[float] = None
    note: Optional[str] = None
    piani_gru_0_1: Optional[str] = None
    piani_2_3: Optional[str] = None
    piani_4_5: Optional[str] = None
    piani_6_7: Optional[str] = None
    image_paths: Optional[List[str]] = None
