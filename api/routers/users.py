from fastapi import APIRouter, Depends, HTTPException
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


# ---------------------------
# CRUD Endpoints
# ---------------------------

@router.get("/all", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db)):
    users = db.exec(select(iUsers)).all()
    return [UserRead.model_validate(u, from_attributes=True) for u in users]



@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(iUsers, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user, from_attributes=True)



@router.post("/add", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    
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
        )
        db.add(entity)

    db.commit()
    return {"users": len(users)}
    