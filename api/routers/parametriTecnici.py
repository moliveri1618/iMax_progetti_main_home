# routes/parametri_tecnici.py
from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List, Optional
from sqlmodel import Session, select

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from models.parametriTecnici import iParametriTecnici
from schemas.parametriTecnici import (
    IParametriTecniciCreate,
    IParametriTecniciRead,
    IParametriTecniciUpdate,
    IParametriTecniciUpsert,
)
from dependecies import get_db

router = APIRouter()

# Get all records
@router.get("", response_model=List[IParametriTecniciRead])
def read_all_parametri(db: Session = Depends(get_db)):
    return db.exec(select(iParametriTecnici)).all()

# Get one by ID
@router.get("/{param_id}", response_model=Optional[IParametriTecniciRead])
def get_parametri_by_id(param_id: int, db: Session = Depends(get_db)):
    entry = db.get(iParametriTecnici, param_id)
    if not entry:
        raise HTTPException(status_code=404, detail="iParametriTecnici not found")
    return entry

# Create
@router.post("", response_model=IParametriTecniciRead, status_code=201)
def create_parametri(input_data: IParametriTecniciCreate, db: Session = Depends(get_db)):
    new_entry = iParametriTecnici(**input_data.dict())
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

# Update (partial)
@router.patch("/{param_id}", response_model=IParametriTecniciRead)
def update_parametri(param_id: int, input_data: IParametriTecniciUpdate, db: Session = Depends(get_db)):
    entry = db.get(iParametriTecnici, param_id)
    if not entry:
        raise HTTPException(status_code=404, detail="iParametriTecnici not found")

    # use exclude_unset to avoid overwriting with None when field not provided
    for field, value in input_data.dict(exclude_unset=True).items():
        setattr(entry, field, value)

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

# Upsert by id (if id present & exists -> update, else create)
@router.post("/upsert", response_model=IParametriTecniciRead)
def upsert_parametri(input_data: IParametriTecniciUpsert, db: Session = Depends(get_db)):
    # If an id is supplied and exists, update; otherwise create a new record
    if input_data.id is not None:
        entry = db.get(iParametriTecnici, input_data.id)
        if entry:
            for field, value in input_data.dict(exclude_unset=True).items():
                if field == "id":
                    continue
                setattr(entry, field, value)
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry

    # Create new
    data = input_data.dict(exclude={"id"})
    new_entry = iParametriTecnici(**data)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

# Delete by ID
@router.delete("/{param_id}", status_code=204)
def delete_parametri(param_id: int, db: Session = Depends(get_db)):
    entry = db.get(iParametriTecnici, param_id)
    if not entry:
        raise HTTPException(status_code=404, detail="iParametriTecnici not found")
    db.delete(entry)
    db.commit()
