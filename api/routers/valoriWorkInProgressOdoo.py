# routers/parametri.py

from fastapi import APIRouter, HTTPException, Depends, status, Body
from sqlmodel import Session, select, delete
from typing import Any, Dict, List, Optional, Sequence
import json
import sys
import os
import httpx


if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
TIMEOUT = 30.0
ODOO_URL="https://odoo.mulattieri.it"
ODOO_URL_LOGIN="https://odoo.mulattieri.it/web/login"
ODOO_URL_API="https://odoo.mulattieri.it/jsonrpc"
DB_NAME="mulsp-odoo-production"     
UID=85 # iMax_api_user
ODOO_BEARER_TOKEN="ocCAF0fVHguW3O*CbTRd*3v9"
WTH_FIREWALL_TOKEN="SK9L6EV4WM934L8YV10HWRE0D5Q6JIG7CF0NGFPWICYCFEKZD58XEIWG2P77"

router = APIRouter()

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

COLONNE = [
    "Elaborazione dati",
    "Ordine a Fornitore",
    "Trasporto al cliente",
    "Trasporto al piano",
    "Smontaggio vecchio",
    "Taglio telai",
    "Posa serramento",
    "Rivestimento Interno",
    "Rilievo Misure",
    "Collaudo Finale",
]

ALIAS = {
    "Costo sviluppo disegni Home": "Elaborazione dati",
    "Costo gestione ordine Home": "Ordine a Fornitore",
    "Costo trasporto al cliente": "Trasporto al cliente",
    "Costo trasporto al piano": "Trasporto al piano",
    "Costo Trasporto al piano": "Trasporto al piano",
    "Costo Smontaggio Vecchio Serramento": "Smontaggio vecchio",
    "Costo Taglio Telai": "Taglio telai",
    "Costo posa in opera Home": "Posa serramento",
    "Costo Riv interno - Esterno": "Rivestimento Interno",
    "Costo Rilievo misure Home": "Rilievo Misure",
    "Costo Collaudo Finale": "Collaudo Finale",
    # Nautica items are intentionally unmapped (ignored)
}

def _pick_value(p: dict):
    v = p.get("value")
    # Treat False/None/"" as missing for floats, use default
    if v in (None, "", False):
        v = p.get("default")
    return v


@router.get("/myOdoo",)
async def get_odoo_product_template(tmpl_id: int = 1):

    products = rpc_call(
        "product.template",
        "search_read",
        [[("id", "=", tmpl_id)]],
        {"fields": ["name", "default_code", "product_properties"]}
    )
    if not products:
        raise HTTPException(status_code=404, detail=f"Template {tmpl_id} not found")

    raw_props = products[0].get("product_properties", [])

    # start with all colonne set to 0 (or None if you prefer)
    normalized: dict[str, float | int | None] = {c: 0 for c in COLONNE}

    for p in raw_props:
        if p.get("type") == "separator":
            continue
        label = p.get("string", "")
        if label in ALIAS:
            normalized[ALIAS[label]] = _pick_value(p)

    return [{"string": c, "value": normalized[c]} for c in COLONNE]

