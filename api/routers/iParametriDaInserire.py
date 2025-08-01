# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
import sys
import os

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import ParametriDaInserireCreate, ParametriDaInserireRead, ParametriDaInserireUpdate
from dependecies import get_db

router = APIRouter(
    prefix="/parametriDaInserire",
    tags=["parametriDaInserire"]
)


# CREATE
@router.post("/", response_model=ParametriDaInserireRead)
def create_parametro(parametro: ParametriDaInserireCreate, session: Session = Depends(ParametriDaInserireRead)):
    db_parametro = ParametriDaInserire.model_validate(parametro)
    session.add(db_parametro)
    session.commit()
    session.refresh(db_parametro)
    return db_parametro


# READ ALL
@router.get("/", response_model=List[ParametriDaInserireRead])
def get_parametri(session: Session = Depends(get_db)):
    parametri = session.exec(select(ParametriDaInserire)).all()
    return parametri


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
