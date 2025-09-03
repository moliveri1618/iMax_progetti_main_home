from typing import List, Optional, Iterable, Dict
from fastapi import HTTPException
from sqlmodel import Session, select, delete
from datetime import datetime, date
from pprint import pprint
from typing import Any, Dict, List, Optional, Sequence
import json
from pydantic import BaseModel, Field
from fpdf import FPDF

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import sys
import os


if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import TEMPLATE_ROWS, MONTHS, MONTH_ORDER, MONTHS_LIST, TRIM_STARTS, TRIM_WEIGHTS
from models.vendite import VenditeImax
from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
from models.iConteggiCommessa import OrdiniPremi


class MaterialeItem(BaseModel):
    materiale: Optional[str] = None
    ordinare: Optional[bool] = None
    magazzino: Optional[bool] = None
    verificare: Optional[bool] = None


class ClienteLavoro(BaseModel):
    id: Optional[int] = None
    cliente: Optional[str] = None
    switch1: Optional[bool] = None
    switch2: Optional[bool] = None
    switch3: Optional[bool] = None


class Tecnico(BaseModel):
    cliente_materiale_mancante: Optional[List[MaterialeItem]] = None
    cliente_materiale_rientrato: Optional[List[MaterialeItem]] = None

    ticket_n: Optional[str] = None
    del_: Optional[str] = Field(default=None, alias="del")  # accepts JSON key "del"
    cliente: Optional[str] = None
    ordine_n: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    telefono_fisso: Optional[str] = None
    cellulare: Optional[str] = None
    persona_rif: Optional[str] = None
    posatore: Optional[str] = None
    squadra: Optional[str] = None
    tempo_previsto_ore: Optional[str] = None
    int_pian_data_ora: Optional[datetime] = None
    ore_previste_riparazioni: Optional[str] = None
    per_numero_posatori: Optional[str] = None

    stato_lavoro: Optional[bool] = None
    informazioni: Optional[bool] = None
    tipo_riparazione: Optional[bool] = None
    fotografie_lavoro_ultimato: Optional[bool] = None
    fotografie_danni_prima_di_iniziare: Optional[bool] = None
    lavoro_non_completato_causa_nostra: Optional[bool] = None
    lavoro_non_completato_causa_cliente: Optional[bool] = None
    danni_vedi_rapporto_posa: Optional[bool] = None
    errore_progettazione: Optional[bool] = None
    errore_scelta_profili_accessori: Optional[bool] = None
    errore_misure_nel_rilievo: Optional[bool] = None
    difficolta_trasporto_non_segnalate: Optional[bool] = None
    errore_calcolo_disposizione: Optional[bool] = None
    vetro_rotto: Optional[bool] = None
    materiale_mancante_non_caricato: Optional[bool] = None
    materiali_posa_mancanti: Optional[bool] = None
    vetro_rotto_posa: Optional[bool] = None
    materiali_profili_danneggiati: Optional[bool] = None
    mancanza_attrezzature: Optional[bool] = None
    danneggiamento_casa_cliente: Optional[bool] = None
    errore_misure_ordine: Optional[bool] = None
    errore_calcolo_tempo_disposizione: Optional[bool] = None
    errore_materiale_contratto: Optional[bool] = None
    cliente_lavori_eseguiti: Optional[List[ClienteLavoro]] = None

    signature: Optional[str] = None

    model_config = {
        "populate_by_name": True,   
        "extra": "ignore",          
    }
    

    
class Cliente(BaseModel):
    cliente_ticket_n: Optional[str] = None
    cliente_del: Optional[str] = None
    cliente_cliente: Optional[str] = None
    ordine_cliente: Optional[str] = None
    indirizzo_cliente: Optional[str] = None
    citta_cliente: Optional[str] = None
    telefono_fisso_cliente: Optional[str] = None
    cellulare_cliente: Optional[str] = None
    persona_di_riferimento_cliente: Optional[str] = None
    posatore_cliente: Optional[str] = None
    squadra_cliente: Optional[str] = None
    tempo_previsto_ore_cliente: Optional[str] = None
    data_cliente: Optional[datetime] = None
    cellulare_cliente_cliente: Optional[str] = None
    signature_cliente_posatore: Optional[str] = None
    signature_cliente_cliente: Optional[str] = None
    note_cliente: Optional[str] = None

class ReportData(BaseModel):
    tecnico: Optional[Tecnico] = None
    cliente: Optional[Cliente] = None  

def order_rows_by_month(rows: Iterable[Dict]) -> List[Dict]:
    """Return rows ordered Gen→Dic using MONTH_ORDER."""
    return sorted(rows, key=lambda r: MONTH_ORDER[str(r["mese"]).strip().lower()])

def json_to_dict(rows: Optional[Sequence[Any]]) -> Optional[List[Dict[str, Any]]]:
    if rows is None:
        return None
    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                # skip or raise depending on your needs
                continue
        if hasattr(r, "model_dump"):     # Pydantic v2 / SQLModel new
            out.append(r.model_dump())
        elif hasattr(r, "dict"):         # Pydantic v1 / SQLModel old
            out.append(r.dict())
        elif isinstance(r, dict):
            out.append(r)
        else:
            raise TypeError(f"Unexpected row type: {type(r)!r}")
    return out

def compute_progressivi_mensili(obiettivi: List[float]) -> List[float]:
    cumul = 0.0
    out: List[float] = []
    for v in obiettivi:
        cumul += v
        out.append(cumul)
    return out

def compute_progressivi_trimestrali(obiettivi: List[float]) -> List[Optional[float]]:
    
    out: List[Optional[float]] = []
    cumul_q = 0.0
    for i, v in enumerate(obiettivi):
        cumul_q += v
        end_of_quarter = (i % 3) == 2  # Mar, Jun, Sep, Dec (0-based)
        if end_of_quarter:
            out.append(cumul_q)
            cumul_q = 0.0
        else:
            out.append(None)
    return out

def _to_datetime(d):
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str):
        # Try common formats + ISO
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(d)  # handles "YYYY-MM-DD HH:MM:SS"
        except Exception:
            return None
    return None

def compute_venduto_reale(db, year=None):
    if year is None:
        year = date.today().year

    sums = [0.0] * 12

    vendite = db.exec(select(VenditeImax)).all()

    for v in vendite:
        dt = _to_datetime(v.data)
        if not dt or dt.year != year:
            continue
        sums[dt.month - 1] += float(v.quantita or 0)

    return sums

def compute_consuntivo_venduto_trimestrale(venduto):
    """
    Quarter-to-date cumulative of Venduto REALE.
    Emit value only at quarter end months; None elsewhere.
    """
    out = []
    acc = 0.0
    for i, v in enumerate(venduto):
        acc += float(v or 0)
        if (i % 3) == 2:        # Mar, Jun, Sep, Dec
            out.append(acc)
            acc = 0.0
        else:
            out.append(None)
    return out

def compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_q, prog_trimestrale):
    """
    Percentage only on quarter ends, None elsewhere.
    """
    out = []
    for c, p in zip(consuntivo_q, prog_trimestrale):
        if c is None or not p:         # not a quarter end or p = 0/None
            out.append(None)
        else:
            out.append((float(c) / float(p)) * 100.0)
    return out

def compute_perc_ragg_fatturato_trimestrale(param_rows):
    """
    Returns a 12-length list: value only on quarter-end months,
    taken from 'perc_premio_trimestrale' in your param rows.
    """
    out = []
    for i, r in enumerate(param_rows):
        out.append(r.get("perc_premio_trimestrale") if (i % 3) == 2 else None)
    return out

def compute_premio_ragg_budget_trimestrale(consuntivo_q, prog_trimestrale, perc_ragg_tri):
    """
    consuntivo_q: quarter-to-date Venduto REALE (value only on Mar/Jun/Sep/Dec; None elsewhere)
    prog_trimestrale: budget quarter total (value only on Mar/Jun/Sep/Dec; None elsewhere)
    perc_ragg_tri: quarter % (value only on Mar/Jun/Sep/Dec; None elsewhere)
    """
    out = []
    for i, (c, p, perc) in enumerate(zip(consuntivo_q, prog_trimestrale, perc_ragg_tri)):
        if (i % 3) != 2:
            out.append(None)                # not a quarter end
            continue
        if c is None or p is None or perc is None:
            out.append(0.0)                 # quarter end but missing data -> 0
            continue
        out.append(c * perc if c >= p else 0.0)
    return out

def compute_premio_ragg_budget_trimestrale(obiettivi, venduto_reale, param_rows):
    """
    For EVERY month:
      IF (QTD consuntivo venduto) >= (quarter budget) THEN QTD * perc_ragg_trimestrale ELSE 0
    - QTD resets at each quarter end.
    - perc_ragg_trimestrale is taken from `perc_premio_trimestrale` on the quarter-end row and
      applied to all 3 months in that quarter.
    """
    # 1) Quarter % spread to all 3 months
    perc_spread = [0.0] * 12
    for q in range(4):
        end = q * 3 + 2  # quarter end index
        row = param_rows[end]
        perc = (row.get("perc_premio_trimestrale")
                if isinstance(row, dict)
                else getattr(row, "perc_premio_trimestrale", 0.0))
        perc_spread[q*3 : q*3 + 3] = [float(perc or 0.0)] * 3

    # 2) Quarter budget repeated across its 3 months
    quarter_budget = []
    for i in range(12):
        start = (i // 3) * 3
        quarter_budget.append(sum(float(x or 0) for x in obiettivi[start:start+3]))

    # 3) Quarter-to-date venduto for each month (reset each quarter)
    venduto_qtd, acc = [], 0.0
    for i, v in enumerate(venduto_reale):
        acc += float(v or 0.0)
        venduto_qtd.append(acc)
        if (i % 3) == 2:
            acc = 0.0

    # 4) Apply your formula per month
    return [(v * p) if (p and v >= b) else 0.0
            for v, b, p in zip(venduto_qtd, quarter_budget, perc_spread)]

def _quarter_progressivo(obiettivi, quarter_idx: int) -> float:
    """Sum of obiettivi for the quarter (equals progressivo trimestrale at Mar/Jun/Sep/Dec)."""
    start = TRIM_STARTS[quarter_idx]
    return float(obiettivi[start] or 0) + float(obiettivi[start+1] or 0) + float(obiettivi[start+2] or 0)

def compute_valori_trimestre(obiettivi, quarter_idx: int):
    """
    Produce a 12-length array for one quarter:
      valori_{quarter} [month] = (quarter progressivo) * weight
    applied over a 7-month window starting at the quarter's first month.
    Wraps around year end for Q4 (Oct..Dec, then Jan..Apr).
    """
    q_prog = _quarter_progressivo(obiettivi, quarter_idx)
    vals = [0.0] * 12
    start = TRIM_STARTS[quarter_idx]
    for k, w in enumerate(TRIM_WEIGHTS):
        i = (start + k) % 12
        vals[i] = q_prog * w
    return vals

def compute_valori_all_trimestri(obiettivi):
    """Returns 4 arrays: valori_1, valori_2, valori_3, valori_4."""
    return (
        compute_valori_trimestre(obiettivi, 0),  # Q1 uses March progressivo
        compute_valori_trimestre(obiettivi, 1),  # Q2 uses June progressivo
        compute_valori_trimestre(obiettivi, 2),  # Q3 uses September progressivo
        compute_valori_trimestre(obiettivi, 3),  # Q4 uses December progressivo
    )

def compute_perc_trim_arrays(perc_al_100, calcolo_percentuale_venduto):
    """
    Build 4 arrays:
      perc_trim_1 = Q * H[Mar], perc_trim_2 = Q * H[Jun],
      perc_trim_3 = Q * H[Sep], perc_trim_4 = Q * H[Dec].

    Notes:
    - We auto-normalize H values: if they look like 0–1 keep as-is, if 0–100 -> divide by 100.
    - Quarter-end month indices (0-based): Mar=2, Jun=5, Sep=8, Dec=11.
    """
    def nz(x):  # none→0 float
        return 0.0 if x is None else float(x)

    def normalize_h(x):
        x = nz(x)
        # If it's percentage like 83 (meaning 83%), scale to 0.83
        return x / 100.0 if x > 1 else x

    # Pick H at quarter ends
    h_mar = normalize_h(calcolo_percentuale_venduto[2])   # H5
    h_jun = normalize_h(calcolo_percentuale_venduto[5])   # H8
    h_sep = normalize_h(calcolo_percentuale_venduto[8])   # H11
    h_dec = normalize_h(calcolo_percentuale_venduto[11])  # H14

    p1 = [nz(q) * h_mar for q in perc_al_100]
    p2 = [nz(q) * h_jun for q in perc_al_100]
    p3 = [nz(q) * h_sep for q in perc_al_100]
    p4 = [nz(q) * h_dec for q in perc_al_100]
    return p1, p2, p3, p4

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def calcola_percentuale_premio(margine, soglie_premi):
    """
    Calcola la percentuale_premio in base al margine e alle soglie.
    soglie_premi deve essere una lista di tuple (soglia, premio), ordinata in modo decrescente.
    """
    for soglia, premio in soglie_premi:
        if margine > soglia:
            return premio

    # fallback → ultimo premio (come R16 in Excel)
    if soglie_premi:
        return soglie_premi[-1][1]
    return None

def create_ordiniPremi_obj(vendite, parametri, user_id):
    
    # estrai coppie (limite, premio) ordinate per valore limite decrescente
    soglie_premi = sorted(
        [(p["valore_limite_perc"], p.get("premio_ragg_budget_annuale")) 
        for p in parametri if p["valore_limite_perc"] is not None],
        key=lambda x: x[0],
        reverse=True
    )


    result = []
    for v in vendite:
            data = parse_date(v["data"])
            venduto_a = v["subtotale"]
            costo_totale = v["costo_unitario"] * v["quantita"]
            margine = venduto_a - costo_totale
            percentuale_ricarico = (margine / costo_totale * 100) if costo_totale else None
            percentuale_premio = calcola_percentuale_premio(margine, soglie_premi)
            valore_premio_lordo = margine * percentuale_premio if percentuale_premio else None

            obj = {
                "user_id": user_id,
                "ordine_numero": v["ordine"],
                "cliente": v["cliente"],
                "prodotto": v["prodotto"],
                "mese": data.strftime("%d/%m/%y"),
                "venduto_a": venduto_a,
                "costo_totale_acquisto": costo_totale,
                "margine": margine,
                "percentuale_ricarico": percentuale_ricarico,
                "percentuale_premio": percentuale_premio,
                "valore_premio_lordo": valore_premio_lordo

            }
            result.append(obj)
            
            
    return result

def delete_replace_ordini_premi(session, user_id: str, rows: List[Dict]) -> int:
    """
    Cancella le righe esistenti in OrdiniPremi per lo user_id e inserisce le nuove.
    Ritorna il numero di righe inserite.
    """
    try:
        # 1) Cancella righe esistenti per questo user
        session.exec(delete(OrdiniPremi).where(OrdiniPremi.user_id == user_id))

        # 2) Inserisci nuove righe
        objs = [OrdiniPremi(user_id=user_id, **{k: v for k, v in row.items() if k != "user_id"}) for row in rows]
        session.add_all(objs)

        # 3) Commit
        session.commit()

        return len(objs)

    except Exception:
        session.rollback()
        raise



def replace_or_insert_parametriDaInserire(
    session: Session,
    user_id: str,
    rows: Optional[Iterable[Dict]] = None,
    *,
    treat_empty_list_as_template: bool = True,
)->int:
    """
    If `rows` is provided:
      - Expect 12 rows covering all months (same shape as TEMPLATE_ROWS).
      - Replace all existing rows for this user atomically.
    If `rows` is None or empty:
      - Seed from TEMPLATE_ROWS.
    """
    uid = str(user_id)

    # Decide source data
    if rows is None or (treat_empty_list_as_template and rows == []):
        source = TEMPLATE_ROWS
    else:
        incoming = [dict(r) for r in rows]  
        for r in incoming:
            r["mese"] = r["mese"].strip().lower()
        months = [r["mese"] for r in incoming]
        if len(incoming) != 12 or len(set(months)) != 12 or set(months) != MONTHS:
            raise HTTPException(
                status_code=422,
                detail="Payload must contain exactly one row for each month (gennaio..dicembre).",
            )
        source = incoming

    # Replace atomically: delete then insert
    try:
        session.exec(delete(ParametriDaInserire).where(ParametriDaInserire.user_id == uid))
        for r in source:
            session.add(ParametriDaInserire(
                user_id=uid,
                mese=r["mese"],
                obiettivo_mensile=r["obiettivo_mensile"],
                perc_premio_trimestrale=r.get("perc_premio_trimestrale"),
                perc_premio_annuale=r.get("perc_premio_annuale"),
                valore_limite=r.get("valore_limite"),
                perc_100_budget=r.get("perc_100_budget"),
            ))
        session.commit()
    except Exception:
        session.rollback()
        raise

    return len(source)

def replace_or_insert_budget_venduto_calcoli(session: Session, user_id: str, rows: List[Dict]) -> None:
    
    try:
        # 1) Delete old rows for the user
        session.exec(delete(BudgetVendutoCalcoli).where(BudgetVendutoCalcoli.user_id == user_id))

        # 2) Insert new rows
        session.add_all([BudgetVendutoCalcoli(**row) for row in rows])
        session.commit()
        return len(rows)
    except Exception:
        session.rollback()
        raise

def replace_or_insert_parametri(parametriDaInserire, session: Session, user_id: str):
    """
    Calculate and save the parametri for the given user_id.
    This function should be called after replace_or_seed_parametri_for_user_core.
    """
    #print('parametriDaInserire', parametriDaInserire)
    
    # Force Gen→Dic order
    ordered = order_rows_by_month([dict(r) for r in parametriDaInserire])

    # Columns calculation
    obiettivi = [row["obiettivo_mensile"] for row in ordered]
    prog_mensili = compute_progressivi_mensili(obiettivi)
    prog_trimestrali = compute_progressivi_trimestrali(obiettivi) 
    venduto_reale = compute_venduto_reale(session, year=None)
    consuntivo_venduto = compute_consuntivo_venduto_trimestrale(venduto_reale)
    perc_rispetto_budget = compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_venduto, prog_trimestrali)
    perc_ragg_fatturato_trimestrale = compute_perc_ragg_fatturato_trimestrale(parametriDaInserire)
    premio_ragg_budget_trimestrale = compute_premio_ragg_budget_trimestrale(obiettivi, venduto_reale, parametriDaInserire)
    valori1, valori2, valori3, valori4 = compute_valori_all_trimestri(obiettivi)
    perc_al_100 = [row["perc_100_budget"] for row in parametriDaInserire]
    perc_trim_1_arr, perc_trim_2_arr, perc_trim_3_arr, perc_trim_4_arr = compute_perc_trim_arrays(perc_al_100, perc_rispetto_budget)
    
    res = []
    totale_obiettivo_mensile = 0 
    totale_obiettivo_trimestrale = 0
    totale_venduto_reale = 0
    totale_consuntivo_venduto = 0
    totale_ragg_budget_trimestrale = 0
    for i, month in enumerate(MONTHS_LIST):
        
        ### Calc totali ###
        # obiettivo_mensile totale
        ob_mens = obiettivi[i] if obiettivi[i] is not None else 0
        totale_obiettivo_mensile += ob_mens
        
        # obiettivo_trimestrale totale
        trim_val = prog_trimestrali[i] if prog_trimestrali[i] is not None else 0
        totale_obiettivo_trimestrale += trim_val
        
        #Venduto reale totale
        venduto_val = venduto_reale[i] if venduto_reale[i] is not None else 0
        totale_venduto_reale += venduto_val
        
        #Totale consuntivo venduto
        consuntivo_val = consuntivo_venduto[i] if consuntivo_venduto[i] is not None else 0
        totale_consuntivo_venduto += consuntivo_val
        
        # TOtale ragg budget trimestrale
        ragg_budget_val = premio_ragg_budget_trimestrale[i] if premio_ragg_budget_trimestrale[i] is not None else 0
        totale_ragg_budget_trimestrale += ragg_budget_val
        
        
        # obiettivi = [row["obiettivo_mensile"] for row in parametriDaInserire]                                       #obiettivo_mensile
        # prog_mensili = compute_progressivi_mensili(obiettivi)                                                       #progressivo_mensile
        # prog_trimestrali = compute_progressivi_trimestrali(obiettivi)                                               #progressivo_trimestrale
        # venduto_reale = compute_venduto_reale(session, year=None) 
        # consuntivo_venduto = compute_consuntivo_venduto_trimestrale(venduto_reale)
        # perc_rispetto_budget = compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_venduto, prog_trimestrali)     
        # perc_ragg_fatturato_trimestrale = compute_perc_ragg_fatturato_trimestrale(parametriDaInserire)
        # premio_ragg_budget_trimestrale = compute_premio_ragg_budget_trimestrale(obiettivi, venduto_reale, parametriDaInserire)
        # valori1, valori2, valori3, valori4 = compute_valori_all_trimestri(obiettivi)
        # perc_al_100 = [row["perc_100_budget"] for row in parametriDaInserire]
        # perc_trim_1_arr, perc_trim_2_arr, perc_trim_3_arr, perc_trim_4_arr = compute_perc_trim_arrays(perc_al_100, perc_rispetto_budget)
        
        
        res.append({
            "user_id": user_id,
            "mese": month,                              
            "obiettivo_mensile": obiettivi[i],
            "progressivo_mensile": prog_mensili[i],
            "progressivo_trimestrale": prog_trimestrali[i],        
            "venduto_reale": venduto_reale[i],
            "consuntivo_venduto": consuntivo_venduto[i], 
            "perc_rispetto_budget": perc_rispetto_budget[i],
            "calcolo_percentuale_venduto": perc_rispetto_budget[i],
            "valore_premio": None,
            "perc_ragg_fatturato_trimestrale": perc_ragg_fatturato_trimestrale[i],
            "premio_ragg_budget_trimestrale": premio_ragg_budget_trimestrale[i],
            "premio_ragg_budget_annuale": parametriDaInserire[i]["perc_premio_annuale"],
            "valori_1_trim": valori1[i],  
            "valori_2_trim": valori2[i],  
            "valori_3_trim": valori3[i],  
            "valori_4_trim": valori4[i],  
            "perc_al_100": perc_al_100[i],
            "perc_trim_1": perc_trim_1_arr[i],
            "perc_trim_2": perc_trim_2_arr[i],
            "perc_trim_3": perc_trim_3_arr[i],
            "perc_trim_4": perc_trim_4_arr[i],
            "valore_limite_perc": parametriDaInserire[i]["valore_limite"],
            
        })
        
    # Add extra "totali" row after the loop
    res.append({
        "user_id": user_id,
        "mese": "totali",
        "obiettivo_mensile": totale_obiettivo_mensile,
        "progressivo_mensile": None,
        "progressivo_trimestrale": totale_obiettivo_trimestrale,
        "venduto_reale": totale_venduto_reale,
        "consuntivo_venduto": totale_consuntivo_venduto,
        "valore_premio": None,
        "premio_ragg_budget_trimestrale": totale_ragg_budget_trimestrale,
        "premio_ragg_budget_annuale": parametriDaInserire[0]["perc_premio_annuale"]
    })
    # print("res")
    # pprint(res)
    
    
    result = replace_or_insert_budget_venduto_calcoli(session, user_id, res)
    return result, res

def replace_or_insert_conteggi_commessa(session: Session, user_id: str, parametri):
    
    # Get vendite for the user
    vendite = session.exec(select(VenditeImax).where(VenditeImax.venditore == "Diana Joita")).scalars().all() # to change!
    vendite = [v.dict() for v in vendite]
    #pprint(parametri)
    #pprint(vendite)
    
    # Create ordiniPremi object 
    res = create_ordiniPremi_obj(vendite, parametri, user_id)
    # print("res:")
    # pprint(res) 
    
    # delete_replace_ordini_premi
    result = delete_replace_ordini_premi(session, user_id, res)
   
    return result

def send_email(pdf_bytes=None, filename="posa_layout.pdf"):
    print("Sending email...")
    
    sender_email = "lastiada1@gmail.com"
    receiver_email = "mauro.oliveri16@gmail.com"
    password = "opqexobtkprukiyi"   # Use environment variable in production!

    subject = "Test Email"
    body = "Hello, this is a test email sent from Python!"

    try:
        
        # Create email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        
        # ✅ attach PDF if provided
        if pdf_bytes:
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(pdf_part)

        # Connect to SMTP and send
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)

        return {"status_code": 200, "result": f"Email sent to {receiver_email}"}


    except smtplib.SMTPAuthenticationError:
        return {"status_code": 401, "error": "Authentication failed. Check SMTP_USER/SMTP_PASS (app password)."}
    except smtplib.SMTPConnectError as e:
        # Connection-level SMTP failure
        err = getattr(e, "smtp_error", b"")
        err = err.decode(errors="ignore") if isinstance(err, bytes) else str(err or e)
        return {"status_code": 503, "error": f"SMTP connect error: {err}"}
    except smtplib.SMTPResponseException as e:
        # Generic 4xx/5xx SMTP response
        code = getattr(e, "smtp_code", 500)
        err = getattr(e, "smtp_error", b"")
        err = err.decode(errors="ignore") if isinstance(err, bytes) else str(err or e)
        return {"status_code": code, "error": err}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}
    
    

def build_report_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def write_cell(w, h, text='', fill=False, align='L', bold=False):
        family = pdf.font_family or "Arial"
        size = pdf.font_size_pt or 12
        style = "B" if bold else ""
        pdf.set_font(family, style=style, size=size)
        pdf.cell(w, h, text, border=1, fill=fill, align=align)

    pdf.set_fill_color(255, 255, 0)  # yellow

    # Header
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Report Commessa Posa in Opera", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(3)

    # Cliente/Ordine row
    write_cell(50, 10, "Cliente", bold=True)
    write_cell(70, 10, data.cliente)
    write_cell(30, 10, "Ordine", bold=True)
    write_cell(40, 10, data.ordine)
    pdf.ln()

    # Squadra/Data row
    write_cell(50, 10, "SQUADRA Posatori", bold=True)
    write_cell(70, 10, data.squadra_posatori)
    write_cell(30, 10, "Data", bold=True)
    write_cell(40, 10, "")  # Not in schema
    pdf.ln()

    # Stato POSA
    write_cell(50, 10, "STATO 1° POSA", bold=True, fill=True)
    write_cell(70, 10, "Completata" if data.stato_posa == "Completata" else "",fill=(data.stato_posa == "Completata"))
    write_cell(70, 10, "Da Completare" if data.stato_posa != "Completata" else "",fill=(data.stato_posa != "Completata"))
    pdf.ln()

    # Resta da fare
    write_cell(190, 10, data.resta_da_fare)
    pdf.ln()

    # Materiale mancante header
    write_cell(80, 10, "Materiale mancante", bold=True)
    write_cell(30, 10, "Ordinare", bold=True)
    write_cell(30, 10, "Magaz.", bold=True)
    write_cell(30, 10, "Verificare", bold=True)
    pdf.ln()

    for item in data.cliente_materiale_mancante:
        write_cell(80, 10, item.materiale)
        write_cell(30, 10, str(item.ordinare).upper(), fill=item.ordinare)
        write_cell(30, 10, str(item.magazzino).upper(), fill=item.magazzino)
        write_cell(30, 10, str(item.verificare).upper(), fill=item.verificare)
        pdf.ln()

    # Materiale rientrato header
    write_cell(80, 10, "Materiale rientrato", bold=True)
    write_cell(30, 10, "Riportare", bold=True)
    write_cell(30, 10, "Reso", bold=True)
    write_cell(30, 10, "Avanzo", bold=True)
    pdf.ln()

    for item in data.cliente_materiale_rientrato:
        write_cell(80, 10, item.materiale)
        write_cell(30, 10, str(item.ordinare).upper(), fill=item.ordinare)
        write_cell(30, 10, str(item.magazzino).upper(), fill=item.magazzino)
        write_cell(30, 10, str(item.verificare).upper(), fill=item.verificare)
        pdf.ln()

    # Ore previste
    write_cell(80, 10, "Ore previste finitura", bold=True)
    write_cell(110, 10, data.ore_previste_finitura)
    pdf.ln()

    write_cell(80, 10, "Per numero posatori", bold=True)
    write_cell(110, 10, data.per_numero_posatori)
    pdf.ln()

    # Notes
    pdf.ln(3)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8,
        "PULIZIA DEI VETRI E/O FINESTRE (CONTROLLO SE PRESENZA DI DIFETTI) - TOGLIERE ETICHETTE\n"
        "GIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZIONALITA'"
    )
    pdf.ln()

    # Extra dummy TRUE/FALSE values if needed
    write_cell(95, 10, "")
    write_cell(30, 10, "FALSE", fill=True)
    write_cell(30, 10, "FALSE", fill=True)
    pdf.ln()

    content = pdf.output(dest='S')
    return content.encode('latin-1') if isinstance(content, str) else content


def build_report_pdf2(data):
    
    
    t = getattr(data, "tecnico", None) or type("Empty", (), {})()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def gv(name, default=""):
        """get value from tecnico, defaulting to '' (or provided) if missing/None"""
        return getattr(t, name, None) if getattr(t, name, None) is not None else default

    def gvl(name):
        """get list value"""
        v = getattr(t, name, None)
        return v if isinstance(v, list) else []

    def gvb(name):
        """get boolean value"""
        v = getattr(t, name, None)
        return bool(v) if v is not None else False

    def fmt_dt(dt):
        v = gv(dt, None)
        if not v:
            return "", ""
        try:
            # pydantic may give datetime already; otherwise ISO string
            d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
            return d.strftime("%d/%m/%Y"), d.strftime("%H:%M")
        except Exception:
            return str(v), ""

    def write_cell(w, h, text='', fill=False, align='L', bold=False):
        family = pdf.font_family or "Arial"
        size = pdf.font_size_pt or 12
        style = "B" if bold else ""
        pdf.set_font(family, style=style, size=size)
        pdf.cell(w, h, text or "", border=1, fill=fill, align=align)

    def bool_cell(label, value, w_label=100, w_box=90):
        write_cell(w_label, 8, label)
        write_cell(w_box, 8, " ", fill=value)

    def section_title(text):
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 9, text, ln=True)
        pdf.set_font("Arial", size=12)
        
    def green_rule(height=3):
        """Draw a full-width green bar at the current Y, then move cursor down."""
        x = pdf.l_margin
        y = pdf.get_y()
        w = pdf.w - pdf.l_margin - pdf.r_margin
        # draw filled green rect (no border)
        pdf.set_fill_color(0, 128, 0)
        pdf.rect(x, y, w, height, style='F')
        pdf.ln(height)
        # restore your default fill color (yellow for cells, per your code)
        pdf.set_fill_color(255, 255, 0)
        
    def green_rule(height=3, x_start=None):
        """Draw a green bar from a given X to the right margin, then move cursor down."""
        if x_start is None:
            x_start = pdf.l_margin  # fallback to left margin

        y = pdf.get_y()
        w = pdf.w - x_start - pdf.r_margin  # width from x_start to right margin

        pdf.set_fill_color(0, 128, 0)
        pdf.rect(x_start, y, w, height, style='F')
        pdf.ln(height)

        # restore default fill color (yellow, per your example)
        pdf.set_fill_color(255, 255, 0)

    def draw_checkbox(pdf, x, y, size=5, checked=False):
        # outer yellow box
        pdf.set_draw_color(0, 0, 0)
        pdf.set_fill_color(255, 235, 59)  # soft yellow (#FFEB3B)
        pdf.rect(x, y, size, size, 'DF')

        # inner light square
        pad = 1.2
        pdf.set_fill_color(245, 245, 245)  # very light gray
        pdf.rect(x + pad, y + pad, size - 2*pad, size - 2*pad, 'F')

        # checkmark if selected
        if checked:
            pdf.set_draw_color(0, 128, 0)
            pdf.set_line_width(0.6)
            pdf.line(x + 0.8, y + size*0.55, x + size*0.45, y + size - 0.9)
            pdf.line(x + size*0.45, y + size - 0.9, x + size - 0.8, y + 1.0)
        pdf.set_line_width(0.2)  # reset

    def three_checkbox_cell_right_optional(
        pdf,
        cell_h,
        materiale,
        ordinare=None,
        magazzino=None,
        verificare=None,
        *,
        green_rgb=(0, 255, 0),
        yellow_rgb=(255, 255, 0),
    ):
        """
        States:
        True   -> green background + checkbox with checkmark
        False  -> yellow background + empty checkbox
        None/""-> horizontal lines only (no box, no fill)
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # Left description cell
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x0, y0, 100, cell_h, 'F')  # fill only, no border
        pdf.set_draw_color(0, 0, 0)
        pdf.line(x0, y0, x0 + 100, y0)              # top line
        pdf.line(x0, y0 + cell_h, x0 + 100, y0 + cell_h)  # bottom line
        pdf.set_xy(x0 + 2, y0)
        pdf.cell(96, cell_h, materiale or "", border=0, align="L")

        def norm_state(v):
            if v is True:
                return "checked"
            if v is False:
                return "unchecked"
            if v is None or (isinstance(v, str) and v.strip() == ""):
                return "empty"
            return "checked" if bool(v) else "unchecked"

        def box_cell(x, v):
            state = norm_state(v)

            if state == "checked":
                pdf.set_fill_color(*green_rgb)
                pdf.rect(x, y0, 30, cell_h, 'DF')
                size = 5
                bx = x + (30 - size) / 2
                by = y0 + (cell_h - size) / 2
                draw_checkbox(pdf, bx, by, size=size, checked=True)

            elif state == "unchecked":
                pdf.set_fill_color(*yellow_rgb)
                pdf.rect(x, y0, 30, cell_h, 'DF')
                size = 5
                bx = x + (30 - size) / 2
                by = y0 + (cell_h - size) / 2
                draw_checkbox(pdf, bx, by, size=size, checked=False)

            else:  # "empty"
                # only horizontal lines (top and bottom)
                pdf.set_draw_color(0, 0, 0)
                pdf.line(x, y0, x + 30, y0)             # top line
                pdf.line(x, y0 + cell_h, x + 30, y0 + cell_h)  # bottom line

        box_cell(x0 + 100, ordinare)
        box_cell(x0 + 130, magazzino)
        box_cell(x0 + 160, verificare)

        pdf.set_xy(x0, y0 + cell_h)

    def three_checkbox_cell_right(pdf, cell_h, materiale,
                                ordinare=False, magazzino=False, verificare=False,
                                green_rgb=(0, 255, 0), yellow_rgb=(255, 255, 0)):
        """
        Draw a row with Materiale description and 3 checkboxes (Ordinare, Magaz., Verificare).
        If checked, cell background is green; otherwise yellow.
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # --- Materiale cell (left column, stays white always) ---
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x0, y0, 100, cell_h, 'DF')
        pdf.set_xy(x0 + 2, y0)
        pdf.cell(100 - 4, cell_h, materiale or "", border=0, align="L")

        # --- Helper for the 3 checkbox cells ---
        def box_cell(x, checked):
            if checked:
                pdf.set_fill_color(*green_rgb)   # green if checked
            else:
                pdf.set_fill_color(*yellow_rgb)  # yellow if not checked
            pdf.rect(x, y0, 30, cell_h, 'DF')

            # Draw checkbox inside
            size = 5
            box_x = x + (30 - size) / 2
            box_y = y0 + (cell_h - size) / 2
            draw_checkbox(pdf, box_x, box_y, size=size, checked=checked)

        # --- Three checkbox cells ---
        box_cell(x0 + 100, ordinare)
        box_cell(x0 + 130, magazzino)
        box_cell(x0 + 160, verificare)

        # --- Move cursor to next row ---
        pdf.set_xy(x0, y0 + cell_h)

    def checkbox_cell_split(pdf, cell_w, cell_h, label, checked, *,
                        font_size=12, box_col_w=10, gap=2,
                        green_rgb=(0, 255, 0), yellow_rgb=(255, 255, 0)):
        """
        [ left column (green if checked, yellow if not) | label column ]
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # Save current font
        cur_font, cur_style, cur_size = pdf.font_family, pdf.font_style, pdf.font_size_pt

        # --- Left column (checkbox area background) ---
        if checked:
            pdf.set_fill_color(*green_rgb)   # green if checked
        else:
            pdf.set_fill_color(*yellow_rgb)  # yellow if not checked
        pdf.rect(x0, y0, box_col_w, cell_h, 'DF')

        # draw the checkbox square inside
        size = 5
        bx = x0 + (box_col_w - size) / 2
        by = y0 + (cell_h - size) / 2
        draw_checkbox(pdf, bx, by, size=size, checked=checked)

        # --- Right column (label) ---
        pdf.set_fill_color(255, 255, 255)  # always white
        pdf.rect(x0 + box_col_w, y0, cell_w - box_col_w, cell_h, 'DF')
        pdf.set_font(cur_font, cur_style, font_size)
        pdf.set_xy(x0 + box_col_w + gap, y0)
        pdf.cell(cell_w - box_col_w - 2*gap, cell_h, label or "", border=0, align="L")


    # region pdf Build Code
    
    # Header
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Report Commessa Posa in Opera", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(3)
    
    
    # Ticket / Del / Data
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Ticket N°", fill=True, bold=True)
    write_cell(60, 8, gv("ticket_n"))
    write_cell(20, 8, "Del", fill=True, bold=True)
    write_cell(80, 8, gv("del"))
    pdf.ln()
    green_rule(height=2)   
    
    # Cliente / Ordine N°
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Cliente", fill=True, bold=True)
    write_cell(60, 8, gv("cliente"))
    write_cell(30, 8, "Ordine N°", fill=True, bold=True)
    write_cell(70, 8, gv("ordine_n"))
    pdf.ln()

    # Indirizzo / Città
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Indirizzo", fill=True, bold=True)
    write_cell(60, 8, gv("indirizzo"))
    write_cell(30, 8, "Città", fill=True, bold=True)
    write_cell(70, 8, gv("citta"))
    pdf.ln()

    # Telefono fisso / Cellulare
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Telefono fisso", fill=True, bold=True)
    write_cell(60, 8, gv("telefono_fisso"))
    write_cell(30, 8, "Cellulare", fill=True, bold=True)
    write_cell(70, 8, gv("cellulare"))
    pdf.ln()
    green_rule(height=2)   

    # Persona di riferimento / Posatore / SQUADRA
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Persona rif", fill=True, bold=True)
    write_cell(60, 8, gv("persona_rif"))
    write_cell(30, 8, "Cellulare", fill=True, bold=True)
    write_cell(70, 8, gv("cellulare"))
    pdf.ln()
    
    # postatore / squadra
    pdf.set_fill_color(230, 230, 230)
    write_cell(30, 8, "Posatore", fill=True, bold=True)
    write_cell(60, 8, gv("posatore"))
    write_cell(30, 8, "SQUADRA", fill=True, bold=True)
    write_cell(70, 8, gv("squadra"))
    pdf.ln()

    # Tempo prev. ore / Intervento pianificato / Data & Ora
    pdf.set_fill_color(230, 230, 230)
    write_cell(50, 8, "Tempo PREVISTO ORE", fill=True, bold=True)
    write_cell(40, 8, gv("tempo_previsto_ore"))
    write_cell(50, 8, "Intervento pianificato x:", fill=True, bold=True)
    date_str, time_str = fmt_dt("int_pian_data_ora")
    pdf.set_fill_color(255, 255, 0)
    write_cell(30, 8, date_str, fill=True)  
    write_cell(20, 8, time_str, fill=True)  
    pdf.ln()
    green_rule(height=2)   
    
    # Stato Lavoro
    pdf.set_fill_color(204, 255, 204) 
    write_cell(50, 8, "STATO LAVORO", bold=True, fill=True)
    checkbox_cell_split(pdf, 60, 8, "Completato", checked=gvb("stato_lavoro"))
    checkbox_cell_split(pdf, 82, 8, "Da Completare", checked=not gvb("stato_lavoro"))
    pdf.ln()
    green_rule(height=2)  

    # Informazioni
    pdf.set_fill_color(204, 255, 204)
    write_cell(50, 8, "Informazioni", bold=True, fill=True)
    checkbox_cell_split(pdf, 60, 8, "Già Cliente", checked=gvb("informazioni"))
    checkbox_cell_split(pdf, 82, 8, "E' STATO ESEGUITO IL SOPRALLUOGO", checked=gvb("informazioni"), font_size=10)  
    pdf.ln()
    green_rule(height=2)  

    # Tipo Riparazione
    pdf.set_fill_color(204, 255, 204)
    write_cell(50, 8, "Tipo Riparazione", bold=True, fill=True)
    checkbox_cell_split(pdf, 60, 8, "Riparazione STD", checked=gvb("tipo_riparazione"))
    checkbox_cell_split(pdf, 82, 8, "Riparazione in Garanzia", checked=(not gvb("tipo_riparazione")))
    pdf.ln()
    
    # Cose da fare
    pdf.set_fill_color(230, 230, 230)
    write_cell(190, 8, "Cose da fare", bold=True, fill=True, align='C')
    pdf.ln()
    
    for item in gvl("cliente_lavori_eseguiti"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        #checkbox_cell_right(pdf, 190, 8, item.cliente or "", checked=bool(item.switch1))
        three_checkbox_cell_right_optional(
            pdf, 8,
            materiale=d.get("cliente"),
            ordinare="",
            magazzino="",
            verificare=d.get("switch1"),
        )
        
    #  Materiale mancante 
    pdf.set_fill_color(230, 230, 230)
    write_cell(100, 8, "Materiale mancante", bold=True, fill=True)
    write_cell(30, 8, "Ordinare", bold=True, fill=True, align="C")
    write_cell(30, 8, "Magaz.", bold=True, fill=True, align="C")
    write_cell(30, 8, "Verificare", bold=True, fill=True, align="C")
    pdf.ln()
    
    for item in gvl("cliente_materiale_mancante"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        three_checkbox_cell_right(
            pdf, 8,
            materiale=d.get("materiale"),
            ordinare=bool(d.get("ordinare")),
            magazzino=bool(d.get("magazzino")),
            verificare=bool(d.get("verificare")),
        )
    
    # Materiale rientrato 
    pdf.set_fill_color(230, 230, 230)
    write_cell(100, 8, "Materiale rientrato", bold=True, fill=True)
    write_cell(30, 8, "Riportare", bold=True, fill=True, align="C")
    write_cell(30, 8, "Reso", bold=True, fill=True, align="C")
    write_cell(30, 8, "Avanzo", bold=True, fill=True, align="C")
    pdf.ln()
    
    for item in gvl("cliente_materiale_rientrato"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        three_checkbox_cell_right(
            pdf, 8,
            materiale=d.get("materiale"),
            ordinare=bool(d.get("ordinare")),
            magazzino=bool(d.get("magazzino")),
            verificare=bool(d.get("verificare")),
        )

    # ---------- Ore previste ----------
    pdf.set_fill_color(230, 230, 230)
    write_cell(60, 8, "Ore previste per finire rip", fill=True, bold=True)
    write_cell(40, 8, gv("ore_previste_riparazioni"))
    write_cell(50, 8, "Per quanti posatori", fill=True, bold=True)
    write_cell(40, 8, gv("per_numero_posatori"))
    pdf.ln()
    
    # FOTOGRAFIE TUTELA DANNI
    pdf.set_fill_color(230, 230, 230)
    three_checkbox_cell_right_optional(
            pdf, 8,
            materiale="FOTOGRAFIE PER TUTELA DANNI PRIMA DI INIZIARE I LAVORI",
            ordinare=None,                 
            magazzino=None,                
            verificare=gvb("fotografie_danni_prima_di_iniziare"),
        )
    # write_cell(190, 8, "Cose da fare", bold=True, fill=True)
    pdf.ln()

    # # ---------- Sezioni tecniche di errore/danni ----------
    # # TECNICO
    # section_title("TECNICO")
    # bool_cell("errore progettazione", gvb("errore_progettazione"))
    # pdf.ln()
    # bool_cell("errore scelta profili e accessori", gvb("errore_scelta_profili_accessori"))
    # pdf.ln()
    # bool_cell("errore misure nel rilievo", gvb("errore_misure_nel_rilievo"))
    # pdf.ln()
    # bool_cell("difficoltà trasporto non segnalate", gvb("difficolta_trasporto_non_segnalate"))
    # pdf.ln()
    # bool_cell("errore calcolo tempo a disposizione", gvb("errore_calcolo_disposizione"))
    # pdf.ln(4)

    # # UFFICIO
    # section_title("UFFICIO")
    # bool_cell("errore misure/materiale/colore nell'ordine", gvb("errore_misure_ordine"))
    # pdf.ln()
    # bool_cell("errore calcolo tempo a disposizione", gvb("errore_calcolo_tempo_disposizione"))
    # pdf.ln(4)

    # # COMMERCIALE
    # section_title("COMMERCIALE")
    # bool_cell("errore materiale/colore nel contratto", gvb("errore_materiale_contratto"))
    # pdf.ln(4)

    # # POSATORI
    # section_title("POSATORI")
    # bool_cell("vetro rotto durante la posa", gvb("vetro_rotto_posa"))
    # pdf.ln()
    # bool_cell("materiali-profili danneggiati durante la posa", gvb("materiali_profili_danneggiati"))
    # pdf.ln()
    # bool_cell("mancanza attrezzature non caricate", gvb("mancanza_attrezzature"))
    # pdf.ln()
    # bool_cell("danneggiamento casa del cliente", gvb("danneggiamento_casa_cliente"))
    # pdf.ln(4)

    # # MAGAZZINO
    # section_title("MAGAZZINO")
    # bool_cell("vetro rotto/difettoso da sostituire", gvb("vetro_rotto"))
    # pdf.ln()
    # bool_cell("materiale mancante non caricato", gvb("materiale_mancante_non_caricato"))
    # pdf.ln()
    # bool_cell("materiali di posa mancanti non caricati", gvb("materiali_posa_mancanti"))
    # pdf.ln(4)

    # # FORNITORE
    # section_title("FORNITORE")
    # bool_cell("materiale difettoso causa fornitore", gvb("errore_materiale_contratto"))  # adjust if you add specific keys
    # pdf.ln(6)

    # # ---------- Note statiche ----------
    # pdf.set_font("Arial", size=10)
    # pdf.multi_cell(0, 7,
    #     "PULIZIA DEI VETRI E/O FINESTRE (CONTROLLO SE PRESENZA DI DIFETTI) - TOGLIERE ETICHETTE\n"
    #     "GIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZIONALITA'"
    # )
    # pdf.ln(2)

    # # ---------- Segnaposto check extra ----------
    # write_cell(95, 8, "")
    # write_cell(30, 8, " ", fill=False)
    # write_cell(30, 8, " ", fill=False)
    # pdf.ln()
    # endregion

    content = pdf.output(dest='S')
    return content.encode('latin-1') if isinstance(content, str) else content
