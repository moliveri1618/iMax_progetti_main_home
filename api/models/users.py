from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class iUsers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.USER)
    capo: Optional[str] = None
    sub: Optional[str] = None