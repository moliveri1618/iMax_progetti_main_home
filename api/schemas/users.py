from typing import Optional
from sqlmodel import SQLModel
from pydantic import BaseModel


# --- Base schema (shared fields) ---
class UserBase(BaseModel):
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None


# --- Create schema ---
class UserCreate(UserBase):
    pass


# --- Read schema ---
class UserRead(SQLModel):
    id: int
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Update schema ---
class UserUpdate(BaseModel):
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
