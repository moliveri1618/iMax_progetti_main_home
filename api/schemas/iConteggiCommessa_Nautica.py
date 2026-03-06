# schemas/ordini_premi.py

from pydantic import BaseModel
from typing import Optional, List
from models.iConteggiCommessa import OrdiniPremi

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


class OrdiniPremiTabLavori(BaseModel):
    id: int
    zona: str
    modello: str
    colonna: str
    completato_da_user: Optional[str] = None
    data_completamento: Optional[str] = None
    nome_cliente: Optional[str] = None
    data: Optional[str] = None
    premio: Optional[float] = None


class OrdiniPremiTabLavori(BaseModel):
    id: int
    ordine_n: str
    zona: str
    modello: str
    colonna: str
    completato_da_user: Optional[str] = None
    data_completamento: Optional[str] = None
    nome_cliente: Optional[str] = None
    data: Optional[str] = None
    premio: Optional[float] = None

    @classmethod
    def from_db(cls, r: OrdiniPremi) -> "OrdiniPremiTabLavori":
        return cls(
            id=r.id,
            ordine_n=r.ordine_numero,
            zona="-",
            modello=r.prodotto or "-",
            colonna="VENDITE NAUTICA",
            completato_da_user=None,
            data_completamento=None,
            nome_cliente=r.cliente,
            data=f"{r.mese}-01" if r.mese else None,
            premio=r.valore_premio_lordo,
        )

    @classmethod
    def from_db_list(cls, rows) -> list["OrdiniPremiTabLavori"]:
        return [cls.from_db(r) for r in rows]
