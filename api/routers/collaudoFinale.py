# Defines API routes and endpoints related to WorkInProgress

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List, Optional
from sqlmodel import Session, select

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))


from models.collaudoFinale import CollaudoFinale
from schemas.collaudoFinale import (
    ICollaudoFinaleCreate,
    ICollaudoFinaleRead,
    ICollaudoFinaleUpdate,
)
from dependecies import get_db

router = APIRouter()


# Get all records
@router.get("", response_model=List[ICollaudoFinaleRead])
def read_all_collaudi(db: Session = Depends(get_db)):
    return db.exec(select(CollaudoFinale)).all()


# Get one by ID
@router.get("/by-workInProgress-id/{work_id}", response_model=Optional[ICollaudoFinaleRead])
def get_collaudo_by_work_id(work_id: int, db: Session = Depends(get_db)):
    entry = db.exec(
        select(CollaudoFinale).where(CollaudoFinale.workInProgress_id == work_id)
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="No collaudo found for this workInProgress_id")
    
    return entry


@router.post("/upsertCollaudo", response_model=ICollaudoFinaleRead)
def upsert_collaudo(input_data: ICollaudoFinaleCreate, db: Session = Depends(get_db)):
    existing_entry = db.exec(
        select(CollaudoFinale).where(CollaudoFinale.workInProgress_id == input_data.workInProgress_id)
    ).first()

    if existing_entry:
        for field, value in input_data.dict().items():
            setattr(existing_entry, field, value)
        db.add(existing_entry)
        db.commit()
        db.refresh(existing_entry)
        return existing_entry
    else:
        new_entry = CollaudoFinale(**input_data.dict())
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry


# Delete by ID
@router.delete("/{collaudo_id}", status_code=204)
def delete_collaudo(collaudo_id: int, db: Session = Depends(get_db)):
    entry = db.get(CollaudoFinale, collaudo_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collaudo finale not found")
    db.delete(entry)
    db.commit()