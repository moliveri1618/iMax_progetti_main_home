# schemas/ordini_premi.py

from pydantic import BaseModel
from typing import Optional, List


class OrdiniPremiBase(BaseModel):
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


class OrdiniPremiCreate(OrdiniPremiBase):
    pass


class OrdiniPremiRead(OrdiniPremiBase):
    id: int


class OrdiniPremiUpdate(BaseModel):
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


class OrdiniPremiBulkUpdateItem(BaseModel):
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


class OrdiniPremiBulkUpdate(BaseModel):
    table: List[OrdiniPremiBulkUpdateItem]
