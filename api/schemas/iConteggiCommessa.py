# schemas/ordini_premi.py

from pydantic import BaseModel
from typing import Optional, List
from models.iConteggiCommessa import OrdiniPremi


MONTHS_IT = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]


def month_key(m: Optional[str]) -> int:
    if not m:
        return 999
    try:
        return MONTHS_IT.index(m.strip().lower())
    except ValueError:
        return 999


def month_to_date_string(mese: Optional[str], year: int = 2026) -> Optional[str]:
    if not mese:
        return None

    mese_clean = mese.strip().lower()

    if mese_clean not in MONTHS_IT:
        return None

    month_number = MONTHS_IT.index(mese_clean) + 1
    return f"{year}-{month_number:02d}-01"


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

    @classmethod
    def from_db(cls, r: OrdiniPremi) -> "OrdiniPremiTabLavori":
        return cls(
            id=r.id,
            zona=r.ordine_numero,
            modello=r.prodotto or "-",
            colonna="VENDITE HOME",
            completato_da_user=None,
            data_completamento=None,
            nome_cliente=r.cliente,
            data=month_to_date_string(r.mese),
            premio=r.valore_premio_lordo,
        )
        
    @classmethod
    def from_db_list(cls, rows) -> list["OrdiniPremiTabLavori"]:
        return [cls.from_db(r) for r in rows]
