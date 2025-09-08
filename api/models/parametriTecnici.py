from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class iParametriTecnici(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    piano_gru_0_1: Optional[float] = None
    piano_2_3: Optional[float] = None
    piano_4_5: Optional[float] = None
    piano_6_7: Optional[float] = None