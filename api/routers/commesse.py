from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.commesse import iCommesse
from schemas.commesse import ICommesseCreate, ICommesseRead, ICommesseUpdate
from dependecies import get_db

router = APIRouter()

# Create
@router.post("", response_model=ICommesseRead)
def create_commessa(commessa: ICommesseCreate, db: Session = Depends(get_db)):
    db_commessa = iCommesse(**commessa.model_dump())
    db.add(db_commessa)
    db.commit()
    db.refresh(db_commessa)
    return db_commessa

# Get all
@router.get("", response_model=List[ICommesseRead])
def read_commesse(db: Session = Depends(get_db)):
    commesse = db.exec(select(iCommesse)).all()
    return commesse

# Get one
@router.get("/{commessa_id}", response_model=ICommesseRead)
def read_commessa(commessa_id: int, db: Session = Depends(get_db)):
    commessa = db.get(iCommesse, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")
    return commessa

# Update
@router.put("/{commessa_id}", response_model=ICommesseRead)
def update_commessa(commessa_id: int, commessa_update: ICommesseUpdate, db: Session = Depends(get_db)):
    commessa = db.get(iCommesse, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")
    update_data = commessa_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(commessa, key, value)
    db.add(commessa)
    db.commit()
    db.refresh(commessa)
    return commessa

# Delete
@router.delete("/{commessa_id}", status_code=204)
def delete_commessa(commessa_id: int, db: Session = Depends(get_db)):
    commessa = db.get(iCommesse, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")
    db.delete(commessa)
    db.commit()
