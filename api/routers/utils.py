from typing import List, Optional, Iterable, Dict
from fastapi import HTTPException
from sqlmodel import Session, select, delete
import sys
import os

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import ParametriRowIn, ParametriBulkUpdate,ParametriDaInserireCreate, ParametriDaInserireRead, ParametriDaInserireUpdate, ParametriDaInserireUpsert, TEMPLATE_ROWS, MONTH_ORDER, MONTHS

# Expect these exist in your module:
# - ParametriDaInserire model
# - TEMPLATE_ROWS (12 items)
# - MONTHS (set of month names)
# - MONTH_ORDER (dict month -> index)

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
    ).all()
    return sorted(out, key=lambda r: MONTH_ORDER.get(r.mese, 99))
