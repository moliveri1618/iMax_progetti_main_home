# schemas/ordini_premi.py

from pydantic import BaseModel
from typing import Optional, List


class OrdiniPremiNauticaBase(BaseModel):
    user_id: Optional[str] = None
    ordine_numero: Optional[str] = None
    cliente: Optional[str] = None
    prodotto: Optional[str] = None
    mese: Optional[str] = None

    venduto_a: Optional[float] = None
    costo_totale_acquisto: Optional[float] = None
    margine: Optional[float] = None
    percentuale_ricarico: Optional[float] = None
    percentuale_premio: Optional[float] = None
    valore_premio_lordo: Optional[float] = None


class OrdiniPremiNauticaCreate(OrdiniPremiNauticaBase):
    pass


class OrdiniPremiNauticaRead(OrdiniPremiNauticaBase):
    id: int


class OrdiniPremiNauticaUpdate(BaseModel):
    user_id: Optional[str] = None
    ordine_numero: Optional[str] = None
    cliente: Optional[str] = None
    prodotto: Optional[str] = None
    mese: Optional[str] = None

    venduto_a: Optional[float] = None
    costo_totale_acquisto: Optional[float] = None
    margine: Optional[float] = None
    percentuale_ricarico: Optional[float] = None
    percentuale_premio: Optional[float] = None
    valore_premio_lordo: Optional[float] = None


class OrdiniPremiNauticaBulkUpdateItem(BaseModel):
    id: Optional[int] = None  # If provided → update, else create new
    ordine_numero: Optional[str] = None
    cliente: Optional[str] = None
    prodotto: Optional[str] = None
    mese: Optional[str] = None

    venduto_a: Optional[float] = None
    costo_totale_acquisto: Optional[float] = None
    margine: Optional[float] = None
    percentuale_ricarico: Optional[float] = None
    percentuale_premio: Optional[float] = None
    valore_premio_lordo: Optional[float] = None


class OrdiniPremiNauticaBulkUpdate(BaseModel):
    table: List[OrdiniPremiNauticaBulkUpdateItem]
