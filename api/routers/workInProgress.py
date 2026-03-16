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
from models.collaudoFinale import CollaudoFinale
from schemas.workInProgress import (
    IWorkInProgressCreate,
    IWorkInProgressRead,
    IWorkInProgressUpdate,
    WorkInProgressGrouped,
    WorkInProgressTabLavori,
)
from schemas.collaudoFinale import (
    ICollaudoFinaleCreate,
    ICollaudoFinaleRead,
    ICollaudoFinaleUpdate,
)
from models.commesse import iCommesse
from models.users import iUsers
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

def remove_zona_duplicates(groups: list[WorkInProgressGrouped]) -> list[WorkInProgressGrouped]:
    """Remove duplicate 'zona' entries, keeping only the first occurrence."""
    seen = set()
    deduped: list[WorkInProgressGrouped] = []
    for g in groups:
        if g.zona in seen:
            continue
        seen.add(g.zona)
        deduped.append(g)
    return deduped

def calc_percentuale_collaudo_finale(
    rilievo_misure: float | None,
    taglio_binario: float | None,
    collaudo_sarte: float | None,
    decimals: int = 1,
) -> float:
    """
    Calculate completion percentage for 'collaudo finale'.

    Each of the three inputs is in [0, 5]. Total max = 15 -> 100%.
    Returns a value between 0 and 100.
    """

    # Treat None as 0
    rm = rilievo_misure or 0.0
    tb = taglio_binario or 0.0
    cs = collaudo_sarte or 0.0

    # Clamp to [0, 5] just in case
    rm = max(0.0, min(5.0, rm))
    tb = max(0.0, min(5.0, tb))
    cs = max(0.0, min(5.0, cs))

    total_steps = rm + tb + cs         # 0..15
    percentage = (total_steps / 15.0) * 100.0

    return round(percentage, decimals)


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
    
    grouped = group_for_frontend(results)
    deduped = remove_zona_duplicates(grouped)
    return deduped

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


# Get all by userEmail
@router.get("/user/{userEmail}", response_model=List[IWorkInProgressRead])
def read_workinprogress_by_user(userEmail: str, db: Session = Depends(get_db)):
    statement = select(WorkInProgress).where(WorkInProgress.completato_da_user == userEmail)
    results = db.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail=f"No records found for user '{userEmail}'")
    return results


# @router.get("/v2/{commessa_id}", response_model=List[WorkInProgressGroupedV2])
@router.get("/v2/{commessa_id}")
def read_workinprogress_v2(commessa_id: int, db: Session = Depends(get_db)):

    # 1) Get all WorkInProgress rows for this commessa
    statement = select(WorkInProgress).where(WorkInProgress.commesse_id == commessa_id)
    results = db.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail="Work in progress not found")

    # 2) Reuse existing grouping logic
    grouped = group_for_frontend(results)
    # deduped = remove_zona_duplicates(grouped)


    # 3) Directly attach CollaudoFinale whenever colonna == "Collaudo Finale"
    for g in grouped:
        for step in g.steps:
            if step.colonna == "Collaudo Finale":
                collaudo_entry = db.exec(
                    select(CollaudoFinale).where(
                        CollaudoFinale.workInProgress_id == step.id
                    )
                ).first()

                if collaudo_entry:
                    step.percentuale_completamento_collaudo_finale = calc_percentuale_collaudo_finale(
                        collaudo_entry.rilievo_misure,
                        collaudo_entry.taglio_binario,
                        collaudo_entry.collaudo_sarte,
                    )
                else:
                    step.percentuale_completamento_collaudo_finale = 0.0

    return grouped


# get work in progress for tabella lavori
@router.get(
    "/tab-lavori/{userEmail}", response_model=list[WorkInProgressTabLavori]
)
def read_workinprogress_tab_lavori_by_user(
    userEmail: str, db: Session = Depends(get_db)
):
    statement = (
        select(
            WorkInProgress,
            iCommesse.ordine,
            iCommesse.data,
            iCommesse.nome_cliente,
            iUsers.bonus_gen,
            iUsers.bonus_capo,
            iUsers.detr_sub,
            iUsers.capo,
            iUsers.sub,
        )
        .join(iCommesse, WorkInProgress.commesse_id == iCommesse.id)
        .join(iUsers, iUsers.email == WorkInProgress.completato_da_user)
        .where(WorkInProgress.completato_da_user == userEmail)
    )
    results = db.exec(statement).all()

    if not results:
        raise HTTPException(
            status_code=404, detail=f"No records found for user '{userEmail}'"
        )

    output = []
    for work, ordine, data, nome_cliente, bonus_gen, bonus_capo, detr_sub, capo, sub in results:

        # convert to dict
        work_dict = (
            IWorkInProgressRead.model_validate(work).model_dump()
            if hasattr(IWorkInProgressRead, "model_validate")
            else IWorkInProgressRead.from_orm(work).dict()
        )

        # calculate bonus gen
        valore = work.valore or 0
        premio = valore * ((bonus_gen or 0) / 100) 

        # calc additional bonus
        if capo and capo != "Empty":
            premio += valore * ((bonus_capo or 0) / 100)
        if sub and sub != "Empty":
            premio -= valore * ((detr_sub or 0) / 100)

        output.append(
            WorkInProgressTabLavori(
                **work_dict,
                ordine_n=ordine,
                data=data,
                nome_cliente=nome_cliente,
                prodotto=f"[{work.zona}] - {work.modello}",
                premio=premio,
            )
        )

    return output
