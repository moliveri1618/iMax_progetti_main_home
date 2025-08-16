# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlmodel import Session, select, delete
from typing import List, Optional
import sys
import os

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import ParametriRowIn, ParametriBulkUpdate,ParametriDaInserireCreate, ParametriDaInserireRead, ParametriDaInserireUpdate, ParametriDaInserireUpsert, TEMPLATE_ROWS, MONTH_ORDER, MONTHS
from dependecies import get_db

router = APIRouter()


@router.put(
    "/parametri/{user_id}",
    response_model=List[ParametriDaInserireRead],
    status_code=status.HTTP_200_OK,
)
def replace_or_seed_parametri_for_user(
    user_id: str,
    rows: Optional[List[ParametriRowIn]] = Body(default=None),
    session: Session = Depends(get_db),
):
    """
    If `rows` is provided:
      - Expect 12 rows covering all months (same shape as TEMPLATE_ROWS).
      - Replace all existing rows for this user atomically.
    If `rows` is None or empty:
      - Seed from TEMPLATE_ROWS.
    """
    uid = str(user_id)

    # Decide source data
    if rows and len(rows) > 0:
        incoming = [r.dict() for r in rows]
        # Normalize month strings
        for r in incoming:
            r["mese"] = r["mese"].strip().lower()
        # Validate: exactly 12, all distinct, all expected months
        months = [r["mese"] for r in incoming]
        if len(incoming) != 12 or len(set(months)) != 12 or set(months) != MONTHS:
            raise HTTPException(
                status_code=422,
                detail="Payload must contain exactly one row for each month (gennaio..dicembre).",
            )
        source = incoming
    else:
        source = TEMPLATE_ROWS

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
    return session.exec(stmt).all()


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

