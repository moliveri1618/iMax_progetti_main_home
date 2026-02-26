from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from fastapi.responses import JSONResponse
from fastapi import Query
import httpx

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.tickets import HelpdeskTicket
from schemas.tickets import TicketCreate, TicketRead, TicketUpdate
from dependecies import get_db

router = APIRouter()

TIMEOUT = 30.0
ODOO_URL="https://odoo.mulattieri.it"
ODOO_URL_LOGIN="https://odoo.mulattieri.it/web/login"
ODOO_URL_API="https://odoo.mulattieri.it/jsonrpc"
DB_NAME="mulsp-odoo-production"     
UID=85 # iMax_api_user
ODOO_BEARER_TOKEN="ocCAF0fVHguW3O*CbTRd*3v9"
WTH_FIREWALL_TOKEN="SK9L6EV4WM934L8YV10HWRE0D5Q6JIG7CF0NGFPWICYCFEKZD58XEIWG2P77"


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


# ---------- GET ALL
@router.get("/all", response_model=List[HelpdeskTicket])
def get_all_tickets(
    db: Session = Depends(get_db),
    type: str = Query("nautica", description="Ticket type: 'nautica', 'home', or 'all'")
):
    try:
        query = select(HelpdeskTicket)

        # If "all" is explicitly requested, skip filtering
        if type.lower() != "all":
            query = query.where(HelpdeskTicket.type == type.lower())

        tickets = db.exec(query).all()
        return tickets

    except Exception as e:
        print(f"Error retrieving tickets: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving tickets from database.")


# ---------- EDIT BY ID
@router.put("/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.get(HelpdeskTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    try:
        # With PUT we expect full object, so no exclude_unset
        updates = payload.model_dump()

        # Optional normalization
        if "type" in updates and updates["type"] is not None:
            updates["type"] = updates["type"].lower()

        for field, value in updates.items():
            setattr(ticket, field, value)

        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    except Exception as e:
        db.rollback()
        print(f"Error updating ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating ticket.")


@router.get("/odoo/v2")
def fetch_helpdesk_tickets_v2(db: Session = Depends(get_db)):
    
    try:
        
        # 1. Search for tickets (no domain = fetch all)
        ticket_ids = rpc_call(
            "ticket.helpdesk",
            "search",
            [[]]
        )
        print(ticket_ids)
        
        # 2. Read ticket data
        tickets = rpc_call(
            "ticket.helpdesk",
            "read",
            [ticket_ids],
            {
                "fields": [
                    "name",         # ticket_ref & name
                    "priority",     # priority
                    "customer_id",  # customer
                    "subject",      #
                    "stage_id",     # stage
                    "tags_ids",     # type
                    "create_date"   # created
                ]
            }
        )
        print(tickets)

        inserted = 0
        skipped = 0
        for t in tickets:


            # ✅ exists check by ticket_ref
            ticket_ref = str(t.get("name") or "")
            if ticket_ref:
                exists_stmt = select(HelpdeskTicket.id).where(HelpdeskTicket.ticket_ref == ticket_ref)
                exists = db.exec(exists_stmt).first()
                if exists:
                    skipped += 1
                    continue


            row = HelpdeskTicket(  
                ticket_ref=str(t.get("name") or ""),
                name=(t.get("name") or ""),
                priority=str(t.get("priority") or ""),
                customer=(t["customer_id"][1] if t.get("customer_id") else ""),
                assigned_to="Unassigned",
                stage=(t["stage_id"][1] if t.get("stage_id") else ""),
                team="N/A",
                created=(t.get("create_date") or ""),
                type=(
                    "nautica" if 2 in (t.get("tags_ids") or [])
                    else "home" if 1 in (t.get("tags_ids") or [])
                    else ""
                ),                
                completato=False,
            )
            db.add(row)
            inserted += 1

        db.commit()
        return {"inserted": inserted}
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
        
    return 1