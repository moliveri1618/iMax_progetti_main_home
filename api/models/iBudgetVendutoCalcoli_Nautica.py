from sqlmodel import SQLModel, Field
from typing import Optional

class BudgetVendutoCalcoliNautica(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)
    
    mese: Optional[str]= Field(default=None)
    obiettivo_mensile: Optional[float] = Field(default=0.0)
    progressivo_mensile: Optional[float] = Field(default=None)
    progressivo_trimestrale: Optional[float] = Field(default=None)
    
    venduto_reale: Optional[float] = Field(default=None)
    consuntivo_venduto: Optional[float] = Field(default=None)
    perc_rispetto_budget: Optional[float] = Field(default=None)
    calcolo_percentuale_venduto: Optional[float] = Field(default=None)
    
    valore_premio: Optional[float] = Field(default=None)
    perc_ragg_fatturato_trimestrale: Optional[float] = Field(default=None)
    premio_ragg_budget_trimestrale: Optional[float] = Field(default=None)
    premio_ragg_budget_annuale: Optional[float] = Field(default=None)
    
    valori_1_trim: Optional[float] = Field(default=None)
    valori_2_trim: Optional[float] = Field(default=None)
    valori_3_trim: Optional[float] = Field(default=None)
    valori_4_trim: Optional[float] = Field(default=None)
    
    perc_al_100: Optional[float] = Field(default=None)
    perc_trim_1: Optional[float] = Field(default=None)
    perc_trim_2: Optional[float] = Field(default=None)
    perc_trim_3: Optional[float] = Field(default=None)
    perc_trim_4: Optional[float] = Field(default=None)
    
    valore_limite_perc: Optional[int] = Field(default=None)
