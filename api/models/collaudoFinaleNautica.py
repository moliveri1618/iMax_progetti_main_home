from sqlmodel import SQLModel, Field
from typing import Optional, List
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column


class CollaudoFinaleNautica(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workInProgress_id: int = Field(foreign_key="workinprogressnautica.id")
    rilievo_misure: Optional[float] = Field(default=None)
    collaudo_sarte: Optional[float] = Field(default=None)
    taglio_binario: Optional[float] = Field(default=None)
    produzione_binari: Optional[float] = Field(default=None)
    assemblaggio_tenda: Optional[float] = Field(default=None)
    lavorazione_sartoria: Optional[float] = Field(default=None)
    image_paths_RM: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )
    image_paths_CS: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )
    image_paths_TB: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )
    image_paths_PB: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    image_paths_AT: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    image_paths_LS: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
