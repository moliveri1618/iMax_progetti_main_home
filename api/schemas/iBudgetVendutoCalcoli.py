from pydantic import BaseModel
from typing import Optional, List

class BudgetVendutoCalcoliBase(BaseModel):
    user_id: Optional[str] = None
    mese: Optional[str] = None
    obiettivo_mensile: Optional[float] = 0.0
    progressivo_mensile: Optional[float] = None
    progressivo_trimestrale: Optional[float] = None

    venduto_reale: Optional[float] = None
    consuntivo_venduto: Optional[float] = None
    perc_rispetto_budget: Optional[float] = None
    calcolo_percentuale_venduto: Optional[float] = None

    valore_premio: Optional[float] = None
    perc_ragg_fatturato_trimestrale: Optional[float] = None
    premio_ragg_budget_trimestrale: Optional[float] = None
    premio_ragg_budget_annuale: Optional[float] = None

    valori_1_trim: Optional[float] = None
    valori_2_trim: Optional[float] = None
    valori_3_trim: Optional[float] = None
    valori_4_trim: Optional[float] = None

    perc_al_100: Optional[float] = None
    perc_trim_1: Optional[float] = None
    perc_trim_2: Optional[float] = None
    perc_trim_3: Optional[float] = None
    perc_trim_4: Optional[float] = None

    valore_limite_perc: Optional[int] = None



class BudgetVendutoCalcoliCreate(BudgetVendutoCalcoliBase):
    pass


class BudgetVendutoCalcoliRead(BudgetVendutoCalcoliBase):
    id: int


class BudgetVendutoCalcoliUpdate(BaseModel):
    user_id: Optional[str] = None
    mese: Optional[str] = None
    obiettivo_mensile: Optional[float] = None
    progressivo_mensile: Optional[float] = None
    progressivo_trimestrale: Optional[float] = None

    venduto_reale: Optional[float] = None
    consuntivo_venduto: Optional[float] = None
    perc_rispetto_budget: Optional[float] = None
    calcolo_percentuale_venduto: Optional[float] = None

    valore_premio: Optional[float] = None
    perc_ragg_fatturato_trimestrale: Optional[float] = None
    premio_ragg_budget_trimestrale: Optional[float] = None
    premio_ragg_budget_annuale: Optional[float] = None

    valori_1_trim: Optional[float] = None
    valori_2_trim: Optional[float] = None
    valori_3_trim: Optional[float] = None
    valori_4_trim: Optional[float] = None

    perc_al_100: Optional[float] = None
    perc_trim_1: Optional[float] = None
    perc_trim_2: Optional[float] = None
    perc_trim_3: Optional[float] = None
    perc_trim_4: Optional[float] = None

    valore_limite_perc: Optional[int] = None


class BudgetVendutoCalcoliBulkUpdateItem(BaseModel):
    id: Optional[int] = None  # If provided → update, else create new
    mese: Optional[str] = None
    obiettivo_mensile: Optional[float] = None
    progressivo_mensile: Optional[float] = None
    progressivo_trimestrale: Optional[float] = None

    venduto_reale: Optional[float] = None
    consuntivo_venduto: Optional[float] = None
    perc_rispetto_budget: Optional[float] = None
    calcolo_percentuale_venduto: Optional[float] = None

    valore_premio: Optional[float] = None
    perc_ragg_fatturato_trimestrale: Optional[float] = None
    premio_ragg_budget_trimestrale: Optional[float] = None
    premio_ragg_budget_annuale: Optional[float] = None

    valori_1_trim: Optional[float] = None
    valori_2_trim: Optional[float] = None
    valori_3_trim: Optional[float] = None
    valori_4_trim: Optional[float] = None

    perc_al_100: Optional[float] = None
    perc_trim_1: Optional[float] = None
    perc_trim_2: Optional[float] = None
    perc_trim_3: Optional[float] = None
    perc_trim_4: Optional[float] = None

    valore_limite_perc: Optional[int] = None


class BudgetVendutoCalcoliBulkUpdate(BaseModel):
    table: List[BudgetVendutoCalcoliBulkUpdateItem]