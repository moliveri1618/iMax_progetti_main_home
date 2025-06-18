from sqlmodel import SQLModel, Field
from typing import Optional, List
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column


class CollaudoFinale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workInProgress_id: int = Field(foreign_key="workinprogress.id")
    rilievo_misure: Optional[float] = Field(default=None)
    collaudo_sarte: Optional[float] = Field(default=None)
    taglio_binario: Optional[float] = Field(default=None)
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
