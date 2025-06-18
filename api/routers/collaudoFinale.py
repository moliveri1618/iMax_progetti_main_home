# Defines API routes and endpoints related to WorkInProgress

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List
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

# Create a new record
@router.post("", response_model=ICollaudoFinaleRead)
def create_collaudo(data: ICollaudoFinaleCreate, db: Session = Depends(get_db)):
    entry = CollaudoFinale(**data.dict())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# Get all records
@router.get("", response_model=List[ICollaudoFinaleRead])
def read_all_collaudi(db: Session = Depends(get_db)):
    return db.exec(select(CollaudoFinale)).all()


# Get one by ID
@router.get("/{collaudo_id}", response_model=ICollaudoFinaleRead)
def read_collaudo(collaudo_id: int, db: Session = Depends(get_db)):
    entry = db.get(CollaudoFinale, collaudo_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collaudo finale not found")
    return entry


# Update by ID
@router.put("/{collaudo_id}", response_model=ICollaudoFinaleRead)
def update_collaudo(collaudo_id: int, data: ICollaudoFinaleUpdate, db: Session = Depends(get_db)):
    entry = db.get(CollaudoFinale, collaudo_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collaudo finale not found")
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# Delete by ID
@router.delete("/{collaudo_id}", status_code=204)
def delete_collaudo(collaudo_id: int, db: Session = Depends(get_db)):
    entry = db.get(CollaudoFinale, collaudo_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collaudo finale not found")
    db.delete(entry)
    db.commit()