from typing import Optional, List
from sqlmodel import SQLModel, Field, ARRAY, Integer, Column
from datetime import date



class WorkInProgressNautica(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    commesse_id: int = Field(foreign_key="icommessenautica.id")  
    zona: str
    modello: str
    colonna: str
    completato: bool
    completato_da_user: str
    data_completamento: Optional[date] = None
    assigned_users_ids: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(ARRAY(Integer), nullable=True),
    )
