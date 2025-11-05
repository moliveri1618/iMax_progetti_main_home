from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class iUsers(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    odoo_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None