# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlmodel import Session, select, delete
from typing import List, Optional
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
from routers.utils import *
from dependecies import get_db

router = APIRouter()


@router.put("/parametri/{user_id}",response_model=Dict[str, int],status_code=status.HTTP_200_OK,)
def replace_or_seed_parametri_for_user(user_id: str,rows: Optional[List[ParametriRowIn]] = Body(default=None),session: Session = Depends(get_db)):
    
    # Insert PARAMETRI DA INSERIRE for user_id
    inserted_rows_parametriDaInserire = replace_or_insert_parametriDaInserire(session=session,user_id=user_id,rows=None if rows is None else [r.model_dump() for r in rows],treat_empty_list_as_template=True,)
    
    # Calculate and save PARAMETRI for user_id
    inserted_rows_parametri, result_parametri = replace_or_insert_parametri(rows if rows else TEMPLATE_ROWS,session=session,user_id=user_id)
    
    # Calculate and save Conteggi Commessa for user_id
    inserted_rows_conteggiCommessa = replace_or_insert_conteggi_commessa(session=session,user_id=user_id,parametri=result_parametri)
    
    return {
        "inserted_rows_parametriDaInserire": inserted_rows_parametriDaInserire,
        "inserted_rows_parametri": inserted_rows_parametri,
        "inserted_rows_conteggiCommessa": inserted_rows_conteggiCommessa,
    }









@router.post("/bulk", response_model=List[ParametriDaInserireRead])
def bulk_upsert(
    payload: ParametriBulkUpdate,
    session: Session = Depends(get_db)
):
    results = []
    for item in payload.table:
        if item.id:
            # Try to get existing row
            parametro_db = session.get(ParametriDaInserire, item.id)
            if parametro_db:
                # Update fields
                for key, value in item.dict(exclude_unset=True).items():
                    setattr(parametro_db, key, value)
                session.add(parametro_db)
                results.append(parametro_db)
            else:
                # If ID given but not found, create new
                new_param = ParametriDaInserire(**item.dict(exclude={"id"}))
                session.add(new_param)
                results.append(new_param)
        else:
            # Create new record
            new_param = ParametriDaInserire(**item.dict(exclude={"id"}))
            session.add(new_param)
            results.append(new_param)

    session.commit()

    # Refresh all updated/created items
    for param in results:
        session.refresh(param)

    return results


# CREATE
@router.post("", response_model=ParametriDaInserireRead)
def create_parametro(
        parametro: ParametriDaInserireCreate, 
        session: Session = Depends(get_db)
    ):
        db_parametro = ParametriDaInserire.model_validate(parametro)
        session.add(db_parametro)
        session.commit()
        session.refresh(db_parametro)
        return db_parametro


# READ ALL or filter by user id if provided
@router.get("", response_model=List[ParametriDaInserireRead])
def get_parametri(user_id: str | None = None, session: Session = Depends(get_db)):
    stmt = select(ParametriDaInserire)
    if user_id:
        stmt = stmt.where(ParametriDaInserire.user_id == user_id)
    items = session.exec(stmt).scalars().all()  
    return items


# READ BY ID
@router.get("/{parametro_id}", response_model=ParametriDaInserireRead)
def get_parametro(parametro_id: int, session: Session = Depends(ParametriDaInserireRead)):
    parametro = session.get(ParametriDaInserire, parametro_id)
    if not parametro:
        raise HTTPException(status_code=404, detail="Parametro not found")
    return parametro


# UPDATE
@router.put("/{parametro_id}", response_model=ParametriDaInserireRead)
def update_parametro(parametro_id: int, parametro_update: ParametriDaInserireUpdate, session: Session = Depends(get_db)):
    parametro_db = session.get(ParametriDaInserire, parametro_id)
    if not parametro_db:
        raise HTTPException(status_code=404, detail="Parametro not found")

    # Update only provided fields
    parametro_data = parametro_update.dict(exclude_unset=True)
    for key, value in parametro_data.items():
        setattr(parametro_db, key, value)

    session.add(parametro_db)
    session.commit()
    session.refresh(parametro_db)
    return parametro_db


# DELETE
@router.delete("/{parametro_id}")
def delete_parametro(parametro_id: int, session: Session = Depends(get_db)):
    parametro = session.get(ParametriDaInserire, parametro_id)
    if not parametro:
        raise HTTPException(status_code=404, detail="Parametro not found")

    session.delete(parametro)
    session.commit()
    return {"message": "Parametro deleted successfully"}

