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
