from sqlmodel import SQLModel, Field
from typing import Optional, List
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column


class RilievoMisure(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workInProgress_id: int = Field(foreign_key="workinprogress.id")
    strada_idonea: Optional[bool] = Field(default=None)
    scala_arrivare_piano: Optional[bool] = Field(default=None)
    ascensore_montacarichi: Optional[bool] = Field(default=None)
    uso_mezzo_vicoli: Optional[bool] = Field(default=None)
    autoscala_tiro_piano: Optional[bool] = Field(default=None)
    spazio_manovra: Optional[bool] = Field(default=None)
    cantiere_nuova_costruzione: Optional[bool] = Field(default=None)
    persone_presenti_scarico: Optional[bool] = Field(default=None)
    numero_persone_scarico: Optional[int] = Field(default=None)
    ztl: Optional[bool] = Field(default=None)
    piani: Optional[str] = Field(default=None)
    trasporto_difficile_piedi_m: Optional[float] = Field(default=None)
    note: Optional[str] = Field(default=None)
    image_paths: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )