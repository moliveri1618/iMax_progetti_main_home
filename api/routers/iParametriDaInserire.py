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

from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import (
    ParametriRowIn,
    ParametriBulkUpdate,
    ParametriDaInserireCreate,
    ParametriDaInserireRead,
    ParametriDaInserireUpdate,
    TEMPLATE_ROWS,
)
from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
from schemas.iBudgetVendutoCalcoli import BudgetVendutoCalcoliRead
from models.iConteggiCommessa import OrdiniPremi
from schemas.iConteggiCommessa import OrdiniPremiRead, OrdiniPremiTabLavori
from models.users import *
from schemas.users import *

from routers.utils import *
from dependecies import get_db

router = APIRouter()


MONTHS_IT = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
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

def recalc_premi_home(
    session: Session = Depends(get_db),
) -> Dict[str, Any]:

    # 1) get distinct user_ids only (tiny result set)
    user_ids: List[str] = session.exec(
        select(ParametriDaInserire.user_id).distinct()
    ).all()

    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    BATCH = 200  # optional: batch users (avoid huge IN clauses if you later optimize further)

    for i in range(0, len(user_ids), BATCH):
        batch_user_ids = user_ids[i : i + BATCH]

        for user_id in batch_user_ids:
            try:
                # 2) load only this user's rows
                user_rows = session.exec(
                    select(ParametriDaInserire).where(
                        ParametriDaInserire.user_id == user_id
                    )
                ).all()

                # if user has no rows, skip
                if not user_rows:
                    continue

                # 3) build payload for your existing function
                payload_rows = [
                    ParametriRowIn(
                        mese=r.mese,
                        obiettivo_mensile=r.obiettivo_mensile,
                        perc_premio_trimestrale=r.perc_premio_trimestrale,
                        perc_premio_annuale=r.perc_premio_annuale,
                        valore_limite=r.valore_limite,
                        perc_100_budget=r.perc_100_budget,
                    )
                    for r in user_rows
                ]

                # ✅ reuse existing function
                results[user_id] = replace_or_seed_parametri_for_user(
                    user_id=user_id,
                    rows=payload_rows,
                    session=session,
                )

            except Exception as e:
                session.rollback()
                errors[user_id] = f"{type(e).__name__}: {str(e)}"

    return {
        "users_processed": len(user_ids),
        "users_ok": len(results),
        "users_failed": len(errors),
        "results": results,
        "errors": errors,
    }


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

    # if no rows, means new user, initiate default calculations
    if rows is None:
        rows = [ParametriRowIn(**r) for r in TEMPLATE_ROWS]
    
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


# recompute vendite calculation for each user in parametri da inserire
@router.post(
    "/parametri/recalc-all-using-existing",
    response_model=Dict[str, Any],
)
def recalc_all_using_replace_or_seed(
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    return recalc_premi_home(session)
    # def recalc_all_using_replace_or_seed(session: Session = Depends(get_db)) -> Dict[str, Any]:

    #     # 1) get distinct user_ids only (tiny result set)
    #     user_ids: List[str] = session.exec(
    #         select(ParametriDaInserire.user_id).distinct()
    #     ).all()

    #     results: Dict[str, Any] = {}
    #     errors: Dict[str, str] = {}

    #     BATCH = 200 # optional: batch users (avoid huge IN clauses if you later optimize further)

    #     for i in range(0, len(user_ids), BATCH):
    #         batch_user_ids = user_ids[i : i + BATCH]

    #         for user_id in batch_user_ids:
    #             try:
    #                 # 2) load only this user's rows
    #                 user_rows = session.exec(
    #                     select(ParametriDaInserire).where(ParametriDaInserire.user_id == user_id)
    #                 ).all()

    #                 # if user has no rows, skip
    #                 if not user_rows:
    #                     continue

    #                 # 3) build payload for your existing function
    #                 payload_rows = [
    #                     ParametriRowIn(
    #                         mese=r.mese,
    #                         obiettivo_mensile=r.obiettivo_mensile,
    #                         perc_premio_trimestrale=r.perc_premio_trimestrale,
    #                         perc_premio_annuale=r.perc_premio_annuale,
    #                         valore_limite=r.valore_limite,
    #                         perc_100_budget=r.perc_100_budget,
    #                     )
    #                     for r in user_rows
    #                 ]

    #                 # ✅ reuse existing function
    #                 results[user_id] = replace_or_seed_parametri_for_user(
    #                     user_id=user_id,
    #                     rows=payload_rows,
    #                     session=session,
    #                 )

    #             except Exception as e:
    #                 session.rollback()
    #                 errors[user_id] = f"{type(e).__name__}: {str(e)}"

    #     return {
    #         "users_processed": len(user_ids),
    #         "users_ok": len(results),
    #         "users_failed": len(errors),
    #         "results": results,
    #         "errors": errors,
    #     }
    # return recalc_all_using_replace_or_seed_service(session)


@router.get(
    "/ordinipremiTabLavori/{user_id}",
    response_model=List[OrdiniPremiTabLavori],
    status_code=status.HTTP_200_OK,
)
def get_ordini_premi_tab_lavori(
    user_id: str,
    session: Session = Depends(get_db),
):
    """
    Return OrdiniPremi formatted for TabLavori frontend table.
    """

    stmt = select(OrdiniPremi).where(OrdiniPremi.user_id == user_id)
    rows = session.exec(stmt).all()
    rows.sort(key=lambda r: month_key(r.mese))

    return OrdiniPremiTabLavori.from_db_list(rows)
