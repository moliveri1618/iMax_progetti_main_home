from typing import Optional
from sqlmodel import SQLModel
from pydantic import BaseModel
from models.tickets import HelpdeskTicket

# Base schema — shared fields (used for Create & Update)
class TicketBase(BaseModel):
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

    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_street: Optional[str] = None
    customer_street2: Optional[str] = None
    customer_zip: Optional[str] = None
    customer_city: Optional[str] = None
    customer_state: Optional[str] = None
    customer_country: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_vat: Optional[str] = None
    customer_website: Optional[str] = None


# Create schema — used for insertions
class TicketCreate(TicketBase):
    pass


# Read schema — used for API responses
class TicketRead(SQLModel):
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

    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_street: Optional[str] = None
    customer_street2: Optional[str] = None
    customer_zip: Optional[str] = None
    customer_city: Optional[str] = None
    customer_state: Optional[str] = None
    customer_country: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_vat: Optional[str] = None
    customer_website: Optional[str] = None

    class Config:
        from_attributes = True


# Update schema — for PATCH operations
class TicketUpdate(BaseModel):
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

    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_street: Optional[str] = None
    customer_street2: Optional[str] = None
    customer_zip: Optional[str] = None
    customer_city: Optional[str] = None
    customer_state: Optional[str] = None
    customer_country: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_vat: Optional[str] = None
    customer_website: Optional[str] = None


class TicketTabLavori(BaseModel):
    ordine_n: str
    prodotto: str
    colonna: str
    data_completamento: Optional[str] = None
    cliente: Optional[str] = None
    data: Optional[str] = None
    premio: Optional[float] = None

    @classmethod
    def from_db(cls, t: HelpdeskTicket, premio: float = 0) -> "TicketTabLavori":
        return cls(
            ordine_n=t.ticket_ref or "",
            prodotto="-",
            colonna="Ticket Home",
            data_completamento=None,
            cliente=t.customer or "",
            data=t.created.split(" ")[0] if t.created else None,
            premio=premio,
        )

    @classmethod
    def from_db_list(cls, rows) -> list["TicketTabLavori"]:
        return [cls.from_db(r) for r in rows]
