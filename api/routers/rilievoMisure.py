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



# Upsert rilievo by ID: create if not exists, otherwise update
@router.put("/{rilievo_id}", response_model=IRilievoRead)
def upsert_rilievo(rilievo_id: int, data: IRilievoUpdate, db: Session = Depends(get_db)):
    rilievo = db.get(RilievoMisure, rilievo_id)
    if rilievo:
        # Update existing record
        for key, value in data.dict(exclude_unset=True).items():
            setattr(rilievo, key, value)
        db.add(rilievo)
    else:
        # Create new record with provided ID
        rilievo = RilievoMisure(id=rilievo_id, **data.dict(exclude_unset=True))
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
