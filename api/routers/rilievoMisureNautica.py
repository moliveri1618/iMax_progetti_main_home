# Defines API routes and endpoints related to WorkInProgress

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List
from sqlmodel import Session, select

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from models.rilievoMisureNautica import RilievoMisureNautica
from models.workInProgressNautica import WorkInProgressNautica 
from schemas.rilievoMisureNautica import IRilievoNauticaCreate, IRilievoNauticaRead, IRilievoNauticaUpdate
from dependecies import get_db

router = APIRouter()


@router.get("/by-commessa-id/{commessa_id}", response_model=List[IRilievoNauticaRead])
def get_rilievi_by_work_id(commessa_id: int, db: Session = Depends(get_db)):
    rilievi = db.exec(
        select(RilievoMisureNautica).where(RilievoMisureNautica.commesse_id == commessa_id)
    ).all()
    
    if not rilievi:
        raise HTTPException(status_code=404, detail="No rilievi found for this workInProgress_id")

    return rilievi

# Upsert rilievo by ID: create if not exists, otherwise update
@router.post("/upsert", response_model=IRilievoNauticaRead)
def upsert_rilievo(input_data: IRilievoNauticaCreate, db: Session = Depends(get_db)):
    existing_rilievo = db.exec(
        select(RilievoMisureNautica).where(RilievoMisureNautica.commesse_id == input_data.commesse_id)
    ).first()

    if existing_rilievo:
        # Update fields
        for field, value in input_data.dict().items():
            setattr(existing_rilievo, field, value)
        db.add(existing_rilievo)
        db.commit()
        db.refresh(existing_rilievo)
        return existing_rilievo
    else:
        # Create new entry
        new_rilievo = RilievoMisureNautica(**input_data.dict())
        db.add(new_rilievo)
        db.commit()
        db.refresh(new_rilievo)
        return new_rilievo


# # Delete rilievo
# @router.delete("/{rilievo_id}", status_code=204)
# def delete_rilievo(rilievo_id: int, db: Session = Depends(get_db)):
#     rilievo = db.get(RilievoMisure, rilievo_id)
#     if not rilievo:
#         raise HTTPException(status_code=404, detail="Rilievo not found")
#     db.delete(rilievo)
#     db.commit()
