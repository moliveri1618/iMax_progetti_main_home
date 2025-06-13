from fastapi import FastAPI
from pydantic import BaseModel
from typing import List 

app = FastAPI()

class MaterialeItem(BaseModel):
    materiale: str
    ordinare: bool
    magazzino: bool
    verificare: bool

class ReportFotografico(BaseModel):
    foto_danni_inizio: bool
    danni_posa_cliente: bool
    foto_giunti_posa: bool
    foto_lavoro_ultimato: bool
    lavoro_non_completato_nostro: bool
    lavoro_non_completato_cliente: bool

class ErroriCategoria(BaseModel):
    errore_progettazione: bool = False
    errore_scelta_profili_accessori: bool = False
    errore_misure_nel_rilievo: bool = False
    difficolta_trasporto_non_segnalate: bool = False
    errore_calcolo_tempo_disp: bool = False

class RecordData(BaseModel):
    cliente: str
    ordine: str
    squadra_posatori: str
    data: str
    stato_posa: str
    resta_da_fare: str
    pulizia_vetri: bool
    giro_cliente: bool
    consegna_documenti: bool
    giro_cliente_conformita: bool
    consegna_libretto: bool
    ddt_verbal_firmati: bool
    difetti_vetri: bool
    difetti_profili: bool
    difetti_muratura: bool
    danni_arrecati: bool
    signature: str
    cliente_cliente: str
    cliente_ordine: str
    cliente_squadra_posatori: str
    cliente_data: str
    cliente_stato_posa: str
    cliente_materiale_mancante: List[MaterialeItem]
    cliente_materiale_rientrato: List[MaterialeItem]
    ore_previste_finitura: str
    per_numero_posatori: str
    report_fotografico: ReportFotografico
    errori: ErroriCategoria
    posatori: ErroriCategoria
    ufficio: ErroriCategoria
    coomerciale: ErroriCategoria
    magazzino: ErroriCategoria
    fornitore: ErroriCategoria
    signature_cliente: str