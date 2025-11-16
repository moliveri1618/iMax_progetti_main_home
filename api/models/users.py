from typing import Optional, Dict
from sqlmodel import SQLModel, Field, Column, JSON
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
    manager: Optional[str] = None
    capo: Optional[str] = None
    sub: Optional[str] = None
    nautica: Dict[str, bool] = Field(
            default_factory=lambda: {
                "Rilievo Misure": False,
                "Collaudo Sarte": False,
                "Taglio Binario": False,
                "Binario Assemblato": False,
                "Tenda Assemblata Bin / Tes Pronta": False,
                "Emesso DDT": False,
                "Attacchi": False,
                "Montaggio a Bordo": False,
                "Filo guidatura": False,
            },
            sa_column=Column(JSON),
        )    
    home: Dict[str, bool] = Field(
        default_factory=lambda: {
            "Rilievo Misure": False,
            "Elaborazione dati e SVILUPPO disegni": False,
            "ORDINE e FORNITORE e controllo conferma": False,
            "TRASPORTO AL CLIENTE": False,
            "TRASPORTO AL PIANO": False,
            "SMONTAGGIO VECCHIO": False,
            "TAGLIO TELAI": False,
            "POSA SERRAMENTO": False,
            "RIVESTIMENTO INTERNO": False,
        },
        sa_column=Column(JSON),
    )
