# routers/budget_venduto_calcoli.py

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
import sys
import os

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
from schemas.iBudgetVendutoCalcoli import (
    BudgetVendutoCalcoliBulkUpdate,
    BudgetVendutoCalcoliCreate,
    BudgetVendutoCalcoliRead,
    BudgetVendutoCalcoliUpdate,
)
from dependecies import get_db

router = APIRouter()


@router.post("/bulk", response_model=List[BudgetVendutoCalcoliRead])
def bulk_upsert(payload: BudgetVendutoCalcoliBulkUpdate, session: Session = Depends(get_db)):
    results: List[BudgetVendutoCalcoli] = []

    for item in payload.table:
        if item.id:
            row = session.get(BudgetVendutoCalcoli, item.id)
            if row:
                for key, value in item.dict(exclude_unset=True).items():
                    setattr(row, key, value)
                session.add(row)
                results.append(row)
            else:
                new_row = BudgetVendutoCalcoli(**item.dict(exclude={"id"}))
                session.add(new_row)
                results.append(new_row)
        else:
            new_row = BudgetVendutoCalcoli(**item.dict(exclude={"id"}))
            session.add(new_row)
            results.append(new_row)

    session.commit()
    for r in results:
        session.refresh(r)
    return results


@router.post("", response_model=BudgetVendutoCalcoliRead)
def create_record(payload: BudgetVendutoCalcoliCreate, session: Session = Depends(get_db)):
    db_row = BudgetVendutoCalcoli.model_validate(payload)
    session.add(db_row)
    session.commit()
    session.refresh(db_row)
    return db_row


@router.get("", response_model=List[BudgetVendutoCalcoliRead])
def list_records(user_id: str | None = None, session: Session = Depends(get_db)):
    stmt = select(BudgetVendutoCalcoli)
    if user_id:
        stmt = stmt.where(BudgetVendutoCalcoli.user_id == user_id)
    return session.exec(stmt).all()


@router.get("/{record_id}", response_model=BudgetVendutoCalcoliRead)
def get_record(record_id: int, session: Session = Depends(get_db)):
    row = session.get(BudgetVendutoCalcoli, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row


@router.put("/{record_id}", response_model=BudgetVendutoCalcoliRead)
def update_record(
    record_id: int,
    payload: BudgetVendutoCalcoliUpdate,
    session: Session = Depends(get_db),
):
    row = session.get(BudgetVendutoCalcoli, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{record_id}")
def delete_record(record_id: int, session: Session = Depends(get_db)):
    row = session.get(BudgetVendutoCalcoli, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    session.delete(row)
    session.commit()
    return {"message": "Record deleted successfully"}
