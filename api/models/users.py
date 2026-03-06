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
    vendite: Optional[bool] = None
    tab_lavori: Optional[bool] = None
    bonus_gen: Optional[int] = None
    bonus_capo: Optional[int] = None
    detr_sub: Optional[int] = None
    riparazioni: Optional[float] = None
    nautica: Dict[str, bool] = Field(
        default_factory=lambda: {
            "Rilievo misure": True,
            "ORDINE e Sviluppo Progetto": True,
            "Taglio Binario": True,
            "Binario Assemblato": True,
            "TAGLIO TESS Sartoria": True,
            "Confezione Sartoria": True,
            "Lavorazioni EXTRA Sartoria": True,
            "Taglio tessuto TECNICO + lavorazioni": True,
            "Bin + Tess. Ass. + imballo": True,
            "Montaggio Attacchi": True,
            "Scarico Trasporto al piano": True,
            "Montaggio Tenda": True,
            "GUIDE e Floggiatura": True,
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
