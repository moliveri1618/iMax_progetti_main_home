from typing import Optional
from sqlmodel import SQLModel
from pydantic import BaseModel
from models.ticketsNautica import HelpdeskTicketNautica


# Base schema — shared fields (used for Create & Update)
class TicketNauticaBase(BaseModel):
    ticket_ref: Optional[str] = None
    name: Optional[str] = None
    priority: Optional[str] = None
    customer: Optional[str] = None
    assigned_to: Optional[str] = None
    stage: Optional[str] = None
    team: Optional[str] = None
    created: Optional[str] = None   # you might switch this to datetime if needed
    type: Optional[str] = None
    completato: Optional[bool] = None
    importo_imponibile: Optional[float] = None


# Create schema — used for insertions
class TicketNauticaCreate(TicketNauticaBase):
    pass


# Read schema — used for API responses
class TicketNauticaRead(SQLModel):
    id: int
    ticket_ref: str
    name: str
    priority: str
    customer: str
    assigned_to: str
    stage: str
    team: str
    created: str
    type: str
    completato: Optional[bool] = None
    importo_imponibile: Optional[float] = None

    class Config:
        from_attributes = True


class TicketNauticaUpdate(BaseModel):
    ticket_ref: Optional[str] = None
    name: Optional[str] = None
    priority: Optional[str] = None
    customer: Optional[str] = None
    assigned_to: Optional[str] = None
    stage: Optional[str] = None
    team: Optional[str] = None
    created: Optional[str] = None
    type: Optional[str] = None
    completato: Optional[bool] = None
    importo_imponibile: Optional[float] = None


# Update schema — for PATCH operations
class TicketNauticaTabLavori(BaseModel):
    ordine_n: str
    prodotto: str
    colonna: str
    data_completamento: Optional[str] = None
    cliente: Optional[str] = None
    data: Optional[str] = None
    premio: Optional[float] = None

    @classmethod
    def from_db(cls, t: HelpdeskTicketNautica, premio: float = 0) -> "TicketNauticaTabLavori":
        return cls(
            ordine_n=t.ticket_ref or "",
            prodotto="-",
            colonna="Ticket Nautica",
            data_completamento=None,
            cliente=t.customer or "",
            data=t.created.split(" ")[0] if t.created else None,
            premio=premio,
        )

    @classmethod
    def from_db_list(cls, rows) -> list["TicketNauticaTabLavori"]:
        return [cls.from_db(r) for r in rows]
