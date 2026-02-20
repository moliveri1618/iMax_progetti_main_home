# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlmodel import Session, select, delete
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Optional, Sequence
import json
import sys
import os

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire_Nautica import ParametriDaInserireNautica  
from schemas.iParametriDaInserire_Nautica import (
    ParametriNauticaRowIn,
    ParametriNauticaBulkUpdate,
    ParametriDaInserireNauticaCreate,
    ParametriDaInserireNauticaRead,
    ParametriDaInserireNauticaUpdate,
    TEMPLATE_ROWS,
)
from models.iBudgetVendutoCalcoli_Nautica import BudgetVendutoCalcoliNautica
from schemas.iBudgetVendutoCalcoli_Nautica import BudgetVendutoCalcoliNauticaRead
from models.iConteggiCommessa_Nautica import OrdiniPremiNautica
from schemas.iConteggiCommessa_Nautica import OrdiniPremiNauticaRead
from models.users import *
from schemas.users import *

from routers.utils import *
from dependecies import get_db

router = APIRouter()



MONTHS_IT = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]

@router.get("/create-parametri-by-user", response_model=List[str])
def list_user_emails(db: Session = Depends(get_db)) -> List[str]:
    users = db.exec(select(iUsers).order_by(iUsers.odoo_id)).all()
    emails = sorted({u.email for u in users if u.email})

    # existing user_ids in ParametriDaInserire
    rows = db.exec(select(ParametriDaInserire.user_id).distinct()).all()
    existing_user_ids = {r[0] if isinstance(r, tuple) else r for r in rows}
    inserted_users: List[str] = []

    for email in emails:
        if email not in existing_user_ids:
            print(f"[SEED] Missing ParametriDaInserire for {email} -> inserting TEMPLATE_ROWS")

            for row in TEMPLATE_ROWS:
                db.add(
                    ParametriDaInserire(
                        user_id=email,
                        mese=row["mese"],
                        obiettivo_mensile=row["obiettivo_mensile"],
                        perc_premio_trimestrale=row["perc_premio_trimestrale"],
                        perc_premio_annuale=row["perc_premio_annuale"],
                        valore_limite=row["valore_limite"],
                        perc_100_budget=row["perc_100_budget"],
                    )
                )
            inserted_users.append(email)

    if inserted_users:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise
        print(f"[SEED] Inserted template rows for: {inserted_users}")

    return emails



@router.put("/parametri/{user_id}",response_model=Dict[str, int],status_code=status.HTTP_200_OK,)
def replace_or_seed_parametri_for_user(user_id: str,rows: Optional[List[ParametriRowIn]] = Body(default=None),session: Session = Depends(get_db)):
    
    # Convert payload to dict if not None
    rows = json_to_dict(rows) 
    
    # Export from ODoo
    fatturato_del_trimestre = compute_quarter_totals_for_user(session=session, user_id=user_id)
    #print('fatturato_del_trimestre', fatturato_del_trimestre)
    
    # Insert PARAMETRI DA INSERIRE for user_id
    inserted_rows_parametriDaInserire = replace_or_insert_parametriDaInserire(session=session,user_id=user_id,rows=rows,treat_empty_list_as_template=True)
    #print('inserted_rows_parametriDaInserire', inserted_rows_parametriDaInserire)
    
    # Calculate and save PARAMETRI for user_id
    inserted_rows_parametri, result_calcoli = replace_or_insert_calcoli(rows if rows else TEMPLATE_ROWS,session=session,user_id=user_id, fatturato_del_trimestre=fatturato_del_trimestre)
    #print('result_calcoli', result_calcoli)
    
    # Calculate and save Conteggi Commessa for user_id
    inserted_rows_conteggiCommessa = replace_or_insert_conteggi_commessa(session=session,user_id=user_id,calcoli=result_calcoli, parametriDiVendita=rows)
    
    return {
        "inserted_rows_parametriDaInserire": inserted_rows_parametriDaInserire,
        "inserted_rows_parametri": inserted_rows_parametri,
        "inserted_rows_conteggiCommessa": inserted_rows_conteggiCommessa,
    }


@router.get(
    "/budget-venduto-calcoli/{user_id}",
    response_model=List[BudgetVendutoCalcoliRead],
    status_code=status.HTTP_200_OK,
)
def get_budget_venduto_calcoli_by_user(
    user_id: str,
    session: Session = Depends(get_db),
):
    """
    Return all BudgetVendutoCalcoli rows for a given user_id,
    sorted by calendar month (gennaio..dicembre).
    """
    stmt = select(BudgetVendutoCalcoli).where(BudgetVendutoCalcoli.user_id == user_id)
    rows = session.exec(stmt).all() 

    def month_key(m: Optional[str]) -> int:
        if not m:
            return 999
        try:
            return MONTHS_IT.index(m.strip().lower())
        except ValueError:
            return 999

    rows.sort(key=lambda r: month_key(r.mese))
    return rows


@router.get(
    "/ordini-premi/{user_id}",
    response_model=List[OrdiniPremiRead],
    status_code=status.HTTP_200_OK,
)
def get_ordini_premi_by_user(
    user_id: str,
    session: Session = Depends(get_db),
):
    """
    Return all OrdiniPremi rows for a given user_id,
    sorted by calendar month (gennaio..dicembre).
    """
    stmt = select(OrdiniPremi).where(OrdiniPremi.user_id == user_id)
    rows = session.exec(stmt).all()  # ensure ORM objects

    def month_key(m: Optional[str]) -> int:
        if not m:
            return 999
        try:
            return MONTHS_IT.index(m.strip().lower())
        except ValueError:
            return 999

    rows.sort(key=lambda r: month_key(r.mese))
    return rows



# READ ALL or filter by user id if provided
@router.get("", response_model=List[ParametriDaInserireRead])
def get_parametri(user_id: str | None = None, session: Session = Depends(get_db)):
    stmt = select(ParametriDaInserire)
    if user_id:
        stmt = stmt.where(ParametriDaInserire.user_id == user_id)
    items = session.exec(stmt).all()  
    return items


