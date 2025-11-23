from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlmodel import Session, select
from typing import List
import sys, os
from fastapi.responses import JSONResponse
import json
import httpx


if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.users import *
from schemas.users import *
from dependecies import get_db

router = APIRouter()

ODOO_URL="https://mulsp-odoocommunitystaging.worthtech.cloud"
ODOO_URL_LOGIN="https://mulsp-odoocommunitystaging.worthtech.cloud/web/login"
ODOO_URL_API="https://mulsp-odoocommunitystaging.worthtech.cloud/jsonrpc"
DB_NAME="mulsp_odoo_staging"
ODOO_BEARER_TOKEN="cd3e8a50bbb79c9bb232940e767961a306e144c0"
WTH_FIREWALL_TOKEN="xt4GSYYeTKzMYfwGk4u5VYU"
UID = 2 
TIMEOUT = 30.0

def rpc_call(model, method, args=None, kwargs=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                DB_NAME,
                UID,
                ODOO_BEARER_TOKEN,
                model,
                method,
                args or [],
                kwargs or {}
            ]
        },
        "id": 1
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ODOO_BEARER_TOKEN}",
        "x-wth-token": WTH_FIREWALL_TOKEN
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(ODOO_URL_API, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise Exception(data["error"])
        return data["result"]


def to_labels(src: Dict[str, bool] | None, mapping: Dict[str, str]) -> Dict[str, bool]:
    if not src:
        return {}

    internal_keys = set(mapping.keys())
    label_keys = set(mapping.values())
    src_keys = set(src.keys())

    has_internal = len(src_keys & internal_keys) > 0
    has_labels   = len(src_keys & label_keys) > 0

    if has_internal and not has_labels:
        # Payload sent with internal keys → map to labels (only keys provided)
        return {mapping[k]: bool(src[k]) for k in src_keys & internal_keys}

    if has_labels:
        # Payload already uses labels → pass through (only known labels)
        return {k: bool(src[k]) for k in src_keys & label_keys}

    # Unknown keys → just pass through as-is
    return {k: bool(v) for k, v in src.items()}



def build_teams_from_users(users: List[iUsers]) -> List[TeamRead]:
    teams: Dict[str, Dict[str, Any]] = {}

    def ensure_team(team_name: str):
        if team_name not in teams:
            teams[team_name] = {
                "name": team_name,
                "managers": [],
                "capi": [],
                "subs": [],
            }

    for u in users:
        # Convert SQLModel -> Pydantic once
        user_read = UserRead.model_validate(u, from_attributes=True)

        # manager team
        if u.manager and u.manager != "Empty":
            ensure_team(u.manager)
            teams[u.manager]["managers"].append(user_read)

        # capo team
        if u.capo and u.capo != "Empty":
            ensure_team(u.capo)
            teams[u.capo]["capi"].append(user_read)

        # sub team
        if u.sub and u.sub != "Empty":
            ensure_team(u.sub)
            teams[u.sub]["subs"].append(user_read)

    # Pydantic will coerce dicts → TeamRead automatically because of response_model
    return [TeamRead(**t) for t in teams.values()]


# ---------------------------
# CRUD Endpoints
# ---------------------------

@router.get("/all", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db)):

    users = db.exec(select(iUsers).order_by(iUsers.odoo_id)).all()
    return [UserRead.model_validate(u, from_attributes=True) for u in users]



@router.get("/sync_odoo", status_code=201)
def sync_user_from_odoo(db: Session = Depends(get_db)):
    
    tmpl_id = 13485  
    users = rpc_call(
        "res.users",
        "search_read",
        [[("active", "=", True)]],
        {"fields": ["id", "name", "login", "email", "company_id", "partner_id", "tz", "lang"], "limit": 20}
    )
    for u in users:
        odoo_user_id = u.get("id")
        if not odoo_user_id:
            continue

        # skip if already in db
        exists = db.exec(select(iUsers).where(iUsers.odoo_id == odoo_user_id)).first()
        if exists:
            continue
        
        comp = u.get("company_id") or [None, None]
        email = (u.get("email") or "").strip()
        role = UserRole.ADMIN if email == "mulsp1@worthtech.cloud" else UserRole.USER

        entity = iUsers(
            odoo_id=odoo_user_id,
            name=u.get("name"),
            email=u.get("email"),
            company_id=comp[0],
            company_name=comp[1],
            role=role,
            manager= "Empty",
            capo= "Empty",
            sub= "Empty",
            nautica={
                "Rilievo Misure": True,
                "Collaudo Sarte": True,
                "Taglio Binario": True,
                "Binario Assemblato": True,
                "Tenda Assemblata Bin / Tes Pronta": True,
                "Emesso DDT": True,
                "Attacchi": True,
                "Montaggio a Bordo": True,
                "Filo guidatura": True,
            },
            home={
                "Rilievo Misure": True,
                "Elaborazione dati e SVILUPPO disegni": True,
                "ORDINE e FORNITORE e controllo conferma": True,
                "TRASPORTO AL CLIENTE": True,
                "TRASPORTO AL PIANO": True,
                "SMONTAGGIO VECCHIO": True,
                "TAGLIO TELAI": True,
                "POSA SERRAMENTO": True,
                "RIVESTIMENTO INTERNO": True,
            },
        )
        db.add(entity)
        
    # Add two extra users manually for testing
    extra_users = [
        iUsers(
            odoo_id=0,
            name="Mauro",
            email="mauro.oliveri16@gmail.com",
            company_id=None,
            company_name=None,
            role=UserRole.ADMIN,
            manager= "Empty",
            capo="Empty",
            sub="Empty",
            nautica={
                "Rilievo Misure": True,
                "Collaudo Sarte": True,
                "Taglio Binario": True,
                "Binario Assemblato": True,
                "Tenda Assemblata Bin / Tes Pronta": True,
                "Emesso DDT": True,
                "Attacchi": True,
                "Montaggio a Bordo": True,
                "Filo guidatura": True,
            },
            home={
                "Rilievo Misure": True,
                "Elaborazione dati e SVILUPPO disegni": True,
                "ORDINE e FORNITORE e controllo conferma": True,
                "TRASPORTO AL CLIENTE": True,
                "TRASPORTO AL PIANO": True,
                "SMONTAGGIO VECCHIO": True,
                "TAGLIO TELAI": True,
                "POSA SERRAMENTO": True,
                "RIVESTIMENTO INTERNO": True,
            },
        ),
        iUsers(
            odoo_id=1,
            name="MauroDue",
            email="Ollimauri775@gmail.com",
            company_id=None,
            company_name=None,
            role=UserRole.USER,
            manager= "Empty",
            capo="Empty",
            sub="Empty",
            nautica={
                "Rilievo Misure": True,
                "Collaudo Sarte": True,
                "Taglio Binario": True,
                "Binario Assemblato": True,
                "Tenda Assemblata Bin / Tes Pronta": True,
                "Emesso DDT": True,
                "Attacchi": True,
                "Montaggio a Bordo": True,
                "Filo guidatura": True,
            },
            home={
                "Rilievo Misure": True,
                "Elaborazione dati e SVILUPPO disegni": True,
                "ORDINE e FORNITORE e controllo conferma": True,
                "TRASPORTO AL CLIENTE": True,
                "TRASPORTO AL PIANO": True,
                "SMONTAGGIO VECCHIO": True,
                "TAGLIO TELAI": True,
                "POSA SERRAMENTO": True,
                "RIVESTIMENTO INTERNO": True,
            },
        )
    ]
    for e in extra_users:
        db.add(e)

    db.commit()
    return {"users": len(users)}


@router.get("/teams", response_model=List[TeamRead])
def list_user_teams(db: Session = Depends(get_db)):
    users = db.exec(select(iUsers)).all()
    return build_teams_from_users(users)    
    
    
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(iUsers, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user, from_attributes=True)


@router.get("/by-email/{email}", response_model=UserRead)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(iUsers).filter(iUsers.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/bulk_upsert")
def bulk_upsert_users(items: List[Dict[str, Any]], db: Session = Depends(get_db)):
    HOME_MAP = {
        "rilievo_misure": "Rilievo Misure",
        "elaborazione_sviluppo": "Elaborazione dati e SVILUPPO disegni",
        "ordine_fornitore": "ORDINE e FORNITORE e controllo conferma",
        "trasporto_cliente": "TRASPORTO AL CLIENTE",
        "trasporto_piano": "TRASPORTO AL PIANO",
        "smontaggio_vecchio": "SMONTAGGIO VECCHIO",
        "taglio_telai": "TAGLIO TELAI",
        "posa_serramento": "POSA SERRAMENTO",
        "rivestimento_interno": "RIVESTIMENTO INTERNO",
    }
    NAUTICA_MAP = {
        "rilievo_misure": "Rilievo Misure",
        "collaudo_sarte": "Collaudo Sarte",
        "taglio_binario": "Taglio Binario",
        "binario_assemblato": "Binario Assemblato",
        "tenda_assemblata": "Tenda Assemblata Bin / Tes Pronta",
        "emesso_ddt": "Emesso DDT",
        "attacchi": "Attacchi",
        "montaggio_a_bordo": "Montaggio a Bordo",
        "filo_guidatura": "Filo guidatura",
    }

    inserted, updated = 0, 0

    for it in items:
        odoo_id = it.get("odoo_id")
        if odoo_id is None:
            continue

        existing = db.exec(select(iUsers).where(iUsers.odoo_id == odoo_id)).first()

        # Prepare mapped fields only if present
        home_labels = to_labels(it.get("home"), HOME_MAP) if "home" in it else None
        nautica_labels = to_labels(it.get("nautica"), NAUTICA_MAP) if "nautica" in it else None
        # print("USER:", odoo_id, it.get("name"), home_labels, nautica_labels)

        if existing:
            changed = False

            if "capo" in it and it["capo"] != existing.capo:
                existing.capo = it["capo"]
                changed = True

            if "sub" in it and it["sub"] != existing.sub:
                existing.sub = it["sub"]
                changed = True
                
            if "manager" in it and it["manager"] != existing.manager:
                existing.manager = it["manager"]
                changed = True
                
            # ✅ auto-admin rule on update (only promote, no demotion)
            if "manager" in it and it["manager"] != "Empty":
                if existing.role != UserRole.ADMIN:
                    existing.role = UserRole.ADMIN
                    changed = True

            if home_labels is not None and home_labels != existing.home:
                existing.home = home_labels
                changed = True

            if nautica_labels is not None and nautica_labels != existing.nautica:
                existing.nautica = nautica_labels
                changed = True

            if changed:
                updated += 1
        else:
            
            manager_val = it.get("manager") or "Empty"
            role_val = UserRole.ADMIN if (manager_val and manager_val != "Empty") else UserRole.USER
            db.add(iUsers(
                odoo_id=odoo_id,
                name=it.get("name"),
                email=it.get("email"),        
                company_id=it.get("company_id"),
                company_name=it.get("company_name"),
                role=role_val,
                manager=manager_val,
                capo=it.get("capo") or "Empty",
                sub=it.get("sub") or "Empty",
                home=home_labels or {},
                nautica=nautica_labels or {},
            ))
            inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "total": len(items)}
    # return 1

