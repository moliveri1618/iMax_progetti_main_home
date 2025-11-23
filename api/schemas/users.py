from typing import Optional, Dict, List
from sqlmodel import SQLModel
from pydantic import BaseModel


# --- Base schema (shared fields) ---
class UserBase(BaseModel):
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    role: Optional[str] = "user"
    manager: Optional[str] = None
    capo: Optional[str] = None
    sub: Optional[str] = None
    nautica: Optional[Dict[str, bool]] = None
    home: Optional[Dict[str, bool]] = None


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
    manager: Optional[str] = None
    role: Optional[str] = "user"
    capo: Optional[str] = None
    sub: Optional[str] = None
    nautica: Optional[Dict[str, bool]] = None
    home: Optional[Dict[str, bool]] = None

    class Config:
        from_attributes = True


# --- Update schema ---
class UserUpdate(BaseModel):
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    manager: Optional[str] = None
    role: Optional[str] = "user"
    capo: Optional[str] = None
    sub: Optional[str] = None
    nautica: Dict[str, bool]
    home: Dict[str, bool]
    
    
class TeamRead(BaseModel):
    name: str
    managers: List[UserRead] = []
    capi: List[UserRead] = []
    subs: List[UserRead] = []