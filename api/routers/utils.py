from typing import List, Optional, Iterable, Dict
from fastapi import HTTPException
from sqlmodel import Session, select, delete
from datetime import datetime, date
from pprint import pprint
from typing import Any, Dict, List, Optional, Sequence
import json

import sys
import os


if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import TEMPLATE_ROWS, MONTHS, MONTH_ORDER, MONTHS_LIST, TRIM_STARTS, TRIM_WEIGHTS
from models.vendite import VenditeImax
from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
from models.iConteggiCommessa import OrdiniPremi

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


def send_email():
    print("Sending email...")
    
    return True