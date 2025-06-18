# Defines API routes and endpoints related to WorkInProgress

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List
from sqlmodel import Session, select

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from models.rilievoMisure import RilievoMisure
from schemas.rilievoMisure import IRilievoCreate, IRilievoRead, IRilievoUpdate
from dependecies import get_db

router = APIRouter()

# Create a new rilievo record
@router.post("", response_model=IRilievoRead)
def create_rilievo(data: IRilievoCreate, db: Session = Depends(get_db)):
    rilievo = RilievoMisure(**data.dict())
    db.add(rilievo)
    db.commit()
    db.refresh(rilievo)
    return rilievo


# Get all rilievi
@router.get("", response_model=List[IRilievoRead])
def read_all_rilievi(db: Session = Depends(get_db)):
    return db.exec(select(RilievoMisure)).all()


# Get one rilievo by ID
@router.get("/{rilievo_id}", response_model=IRilievoRead)
def read_rilievo(rilievo_id: int, db: Session = Depends(get_db)):
    rilievo = db.get(RilievoMisure, rilievo_id)
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo not found")
    return rilievo


# Update rilievo by ID
@router.put("/{rilievo_id}", response_model=IRilievoRead)
def update_rilievo(rilievo_id: int, update_data: IRilievoUpdate, db: Session = Depends(get_db)):
    rilievo = db.get(RilievoMisure, rilievo_id)
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo not found")
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(rilievo, key, value)
    db.add(rilievo)
    db.commit()
    db.refresh(rilievo)
    return rilievo


# Delete rilievo
@router.delete("/{rilievo_id}", status_code=204)
def delete_rilievo(rilievo_id: int, db: Session = Depends(get_db)):
    rilievo = db.get(RilievoMisure, rilievo_id)
    if not rilievo:
        raise HTTPException(status_code=404, detail="Rilievo not found")
    db.delete(rilievo)
    db.commit()
