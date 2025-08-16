from typing import List, Optional, Iterable, Dict
from fastapi import HTTPException
from sqlmodel import Session, select, delete
from datetime import datetime, date
from sqlalchemy import select
import sys
import os
from pprint import pprint

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import ParametriRowIn, ParametriBulkUpdate,ParametriDaInserireCreate, ParametriDaInserireRead, ParametriDaInserireUpdate, ParametriDaInserireUpsert, TEMPLATE_ROWS, MONTH_ORDER, MONTHS
from models.vendite import VenditeImax

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

    # KEY: use .scalars() so we get VenditeImax instances, not Row tuples
    vendite = db.exec(select(VenditeImax)).scalars().all()

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





def replace_or_seed_parametri_for_user_core(
    session: Session,
    user_id: str,
    rows: Optional[Iterable[Dict]] = None,
    *,
    treat_empty_list_as_template: bool = True,
) -> List["ParametriDaInserire"]:
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
        incoming = [dict(r) for r in rows]  # defensive copy, accept list[dict] or pydantic models' .dict()
        # Normalize months
        for r in incoming:
            r["mese"] = r["mese"].strip().lower()
        # Validate: exactly 12 and all expected months
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

    # Return ordered
    out = session.exec(
        select(ParametriDaInserire).where(ParametriDaInserire.user_id == uid)
    ).scalars().all()

    return sorted(out, key=lambda r: MONTH_ORDER.get((r.mese or "").lower(), 99))

def calculate_and_save_parametri(parametriDaInserire, session: Session, user_id: str):
    """
    Calculate and save the parametri for the given user_id.
    This function should be called after replace_or_seed_parametri_for_user_core.
    """
    pprint('parametriDaInserire', parametriDaInserire, sort_dicts=False, width=120)
    
    res = []
    for i, month in enumerate(MONTHS):
        
        obiettivi = [row["obiettivo_mensile"] for row in parametriDaInserire]                                       #obiettivo_mensile
        prog_mensili = compute_progressivi_mensili(obiettivi)                                                       #progressivo_mensile
        prog_trimestrali = compute_progressivi_trimestrali(obiettivi)                                               #progressivo_trimestrale
        venduto_reale = compute_venduto_reale(session, year=None) 
        consuntivo_venduto = compute_consuntivo_venduto_trimestrale(venduto_reale)
        perc_rispetto_budget = compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_venduto, prog_trimestrali)     
        perc_ragg_fatturato_trimestrale = compute_perc_ragg_fatturato_trimestrale(parametriDaInserire)
        premio_ragg_budget_trimestrale = compute_premio_ragg_budget_trimestrale(consuntivo_venduto, prog_trimestrali, perc_ragg_fatturato_trimestrale)
        
        res.append({
            "user_id": user_id,
            "mese": month,                              
            "obiettivo_mensile": obiettivi[i],
            "progressivo_mensile": prog_mensili[i],
            "progressivo_trimestrale": prog_trimestrali[i],        
            "venduto_reale": venduto_reale[i],
            "consuntivo_venduto": consuntivo_venduto[i], 
            "perc_rispetto_budget": perc_rispetto_budget[i],
            "calcolo_percentuale_venduto": None,
            "valore_premio": None,
            "perc_ragg_fatturato_trimestrale": perc_ragg_fatturato_trimestrale[i],
            "premio_ragg_budget_trimestrale": premio_ragg_budget_trimestrale[i],
            "premio_ragg_budget_annuale": parametriDaInserire[i]["perc_premio_annuale"],
            
        })
    pprint("res", res, sort_dicts=False, width=120)


    
    return 1