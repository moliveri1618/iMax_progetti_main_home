from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class OrdiniPremi(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)

    ordine_numero: Optional[str]= Field(default=None) 
    cliente: Optional[str]= Field(default=None)
    prodotto: Optional[str]= Field(default=None)
    mese: Optional[str]= Field(default=None)  

    venduto_a: Optional[float] = Field(default=None)
    costo_totale_acquisto: Optional[float] = Field(default=None)
    margine: Optional[float] = Field(default=None)
    percentuale_ricarico: Optional[float] = Field(default=None)
    percentuale_premio: Optional[float] = Field(default=None)
    valore_premio_lordo: Optional[float] = Field(default=None)
