from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class HelpdeskTicketNautica(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_ref: str
    name: str
    priority: str
    customer: str
    assigned_to: str
    stage: str
    team: str
    created: str
    type: str  
    importo_imponibile: float
    completato: Optional[bool]= Field(default=False) 
