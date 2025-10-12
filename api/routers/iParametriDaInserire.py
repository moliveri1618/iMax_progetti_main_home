# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlmodel import Session, select, delete
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
from schemas.iConteggiCommessa import OrdiniPremiRead

from routers.utils import *
from dependecies import get_db

router = APIRouter()


MONTHS_IT = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]

@router.put("/parametri/{user_id}",response_model=Dict[str, int],status_code=status.HTTP_200_OK,)
def replace_or_seed_parametri_for_user(user_id: str,rows: Optional[List[ParametriRowIn]] = Body(default=None),session: Session = Depends(get_db)):
    
    # Convert payload to dict if not None
    rows = json_to_dict(rows) 
    
    # TODO: replace with real API call
    # Export from ODoo
    fatturato_del_trimestre = {
        '1_trimestre': 10000.0,
        '2_trimestre': 15000.0,
        '3_trimestre': 20000.0,
        '4_trimestre': 25000.0
    }

    # # Calculate and save Conteggi Commessa for user_id
    # inserted_rows_conteggiCommessa = replace_or_insert_conteggi_commessa(session=session,user_id=user_id,parametri=result_parametri)
    
    # Insert PARAMETRI DA INSERIRE for user_id
    inserted_rows_parametriDaInserire = replace_or_insert_parametriDaInserire(session=session,user_id=user_id,rows=rows,treat_empty_list_as_template=True)
    
    # Calculate and save PARAMETRI for user_id
    inserted_rows_parametri = replace_or_insert_calcoli(rows if rows else TEMPLATE_ROWS,session=session,user_id=user_id, fatturato_del_trimestre=fatturato_del_trimestre)
    
    
    return {
        "inserted_rows_parametriDaInserire": inserted_rows_parametriDaInserire,
        "inserted_rows_parametri": inserted_rows_parametri,
        #"inserted_rows_conteggiCommessa": inserted_rows_conteggiCommessa,
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


# @router.post("/bulk", response_model=List[ParametriDaInserireRead])
# def bulk_upsert(
#     payload: ParametriBulkUpdate,
#     session: Session = Depends(get_db)
# ):
#     results = []
#     for item in payload.table:
#         if item.id:
#             # Try to get existing row
#             parametro_db = session.get(ParametriDaInserire, item.id)
#             if parametro_db:
#                 # Update fields
#                 for key, value in item.dict(exclude_unset=True).items():
#                     setattr(parametro_db, key, value)
#                 session.add(parametro_db)
#                 results.append(parametro_db)
#             else:
#                 # If ID given but not found, create new
#                 new_param = ParametriDaInserire(**item.dict(exclude={"id"}))
#                 session.add(new_param)
#                 results.append(new_param)
#         else:
#             # Create new record
#             new_param = ParametriDaInserire(**item.dict(exclude={"id"}))
#             session.add(new_param)
#             results.append(new_param)

#     session.commit()

#     # Refresh all updated/created items
#     for param in results:
#         session.refresh(param)

#     return results


# # CREATE
# @router.post("", response_model=ParametriDaInserireRead)
# def create_parametro(
#         parametro: ParametriDaInserireCreate, 
#         session: Session = Depends(get_db)
#     ):
#         db_parametro = ParametriDaInserire.model_validate(parametro)
#         session.add(db_parametro)
#         session.commit()
#         session.refresh(db_parametro)
#         return db_parametro


# # READ BY ID
# @router.get("/{parametro_id}", response_model=ParametriDaInserireRead)
# def get_parametro(parametro_id: int, session: Session = Depends(ParametriDaInserireRead)):
#     parametro = session.get(ParametriDaInserire, parametro_id)
#     if not parametro:
#         raise HTTPException(status_code=404, detail="Parametro not found")
#     return parametro


# # UPDATE
# @router.put("/{parametro_id}", response_model=ParametriDaInserireRead)
# def update_parametro(parametro_id: int, parametro_update: ParametriDaInserireUpdate, session: Session = Depends(get_db)):
#     parametro_db = session.get(ParametriDaInserire, parametro_id)
#     if not parametro_db:
#         raise HTTPException(status_code=404, detail="Parametro not found")

#     # Update only provided fields
#     parametro_data = parametro_update.dict(exclude_unset=True)
#     for key, value in parametro_data.items():
#         setattr(parametro_db, key, value)

#     session.add(parametro_db)
#     session.commit()
#     session.refresh(parametro_db)
#     return parametro_db


# # DELETE
# @router.delete("/{parametro_id}")
# def delete_parametro(parametro_id: int, session: Session = Depends(get_db)):
#     parametro = session.get(ParametriDaInserire, parametro_id)
#     if not parametro:
#         raise HTTPException(status_code=404, detail="Parametro not found")

#     session.delete(parametro)
#     session.commit()
#     return {"message": "Parametro deleted successfully"}

