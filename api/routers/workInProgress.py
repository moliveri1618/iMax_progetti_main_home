# Defines API routes and endpoints related to WorkInProgress

from fastapi import APIRouter, Depends, HTTPException
import sys
import os
from typing import List
from sqlmodel import Session, select
from itertools import groupby

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from models.workInProgress import WorkInProgress
from schemas.workInProgress import IWorkInProgressCreate, IWorkInProgressRead, IWorkInProgressUpdate, WorkInProgressGrouped
from dependecies import get_db

router = APIRouter()

def group_for_frontend(rows):
    
    # Stable order so partitioning is deterministic
    rows_sorted = sorted(rows, key=lambda r: (r.zona or "", r.modello or "", r.id))
    out = []

    for (zona, modello), grp in groupby(rows_sorted, key=lambda r: (r.zona or "", r.modello or "")):
        batches = []
        current, seen = [], set()

        for r in list(grp):
            
            # If this colonna already exists in the current batch, start a new batch
            if r.colonna in seen:
                batches.append(current)
                current, seen = [], set()
            current.append(r)
            seen.add(r.colonna)

        if current:
            batches.append(current)

        # Emit one WorkInProgressGrouped per batch
        for batch in batches:
            steps = [
                (IWorkInProgressRead.model_validate(x) if hasattr(IWorkInProgressRead, "model_validate")
                 else IWorkInProgressRead.from_orm(x))
                for x in batch
            ]
            out.append(WorkInProgressGrouped(zona=zona, modello=modello, steps=steps))

    return out



# Create
@router.post("", response_model=IWorkInProgressRead)
def create_workinprogress(work: IWorkInProgressCreate, db: Session = Depends(get_db)):
    db_work = WorkInProgress(**work.dict())
    db.add(db_work)
    db.commit()
    db.refresh(db_work)
    return db_work


# Get all
@router.get("", response_model=List[IWorkInProgressRead])
def read_all_workinprogress(db: Session = Depends(get_db)):
    return db.exec(select(WorkInProgress)).all()


# Get one
@router.get("/{commessa_id}", response_model=List[WorkInProgressGrouped])
def read_workinprogress(commessa_id: int, db: Session = Depends(get_db)):
    statement = select(WorkInProgress).where(WorkInProgress.commesse_id == commessa_id)
    results = db.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail="Work in progress not found")
    return group_for_frontend(results)


# Update
@router.put("/{work_id}", response_model=IWorkInProgressRead)
def update_workinprogress(work_id: int, update_data: IWorkInProgressUpdate, db: Session = Depends(get_db)):
    #print("Update data:", update_data)
    work = db.get(WorkInProgress, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work in progress not found")
    update_fields = update_data.dict(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(work, key, value)
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


# Delete
@router.delete("/{work_id}", status_code=204)
def delete_workinprogress(work_id: int, db: Session = Depends(get_db)):
    work = db.get(WorkInProgress, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work in progress not found")
    db.delete(work)
    db.commit()


# Get all by username
@router.get("/user/{username}", response_model=List[IWorkInProgressRead])
def read_workinprogress_by_user(username: str, db: Session = Depends(get_db)):
    statement = select(WorkInProgress).where(WorkInProgress.completato_da_user == username)
    results = db.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail=f"No records found for user '{username}'")
    return results
