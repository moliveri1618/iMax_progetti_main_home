from typing import Optional
from sqlmodel import SQLModel
from pydantic import BaseModel


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
