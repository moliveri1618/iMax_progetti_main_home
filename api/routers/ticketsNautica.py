from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from fastapi.responses import JSONResponse
from fastapi import Query
import httpx

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.ticketsNautica import HelpdeskTicketNautica
from schemas.ticketsNautica import TicketNauticaCreate, TicketNauticaRead, TicketNauticaUpdate
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
@router.get("/all", response_model=List[TicketNauticaRead])
def get_all_tickets(
    db: Session = Depends(get_db),
    type: str = Query("nautica", description="Ticket type: 'nautica', 'home', or 'all'")
):
    try:
        query = select(HelpdeskTicketNautica)

        # If "all" is explicitly requested, skip filtering
        if type.lower() != "all":
            query = query.where(HelpdeskTicketNautica.type == type.lower())
        tickets = db.exec(query).all()
        return tickets

    except Exception as e:
        print(f"Error retrieving tickets: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving tickets from database.")


# ---------- EDIT BY ID
@router.put("/{ticket_id}", response_model=TicketNauticaRead)
def update_ticket(ticket_id: int, payload: TicketNauticaUpdate, db: Session = Depends(get_db)):
    ticket = db.get(HelpdeskTicketNautica, ticket_id)
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




# @router.get("/odoo")
# def fetch_helpdesk_tickets(db: Session = Depends(get_db)):

#     # Connect to the common service and authenticate
#     models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')
#     common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
#     user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})

#     try:
#         # 1. Search for tickets (no domain = fetch all)
#         ticket_ids = models.execute_kw(
#             DB_NAME_ODOO, user_id, PASSWORD_ODOO,
#             'helpdesk.ticket', 'search',
#             [[]]
#         )

#         # 2. Read ticket data
#         tickets = models.execute_kw(
#             DB_NAME_ODOO, user_id, PASSWORD_ODOO,
#             'helpdesk.ticket', 'read',
#             [ticket_ids],
#             {'fields': [
#                 'ticket_ref',
#                 'name',
#                 'priority',
#                 'partner_id',
#                 'user_id',
#                 'stage_id',
#                 'team_id',
#                 'create_date',
#             ]}
#         )

#         # 3. Check if tickets already exist in the database and insert new ones
#         count = 0
#         for t in tickets:
#             team_name = t['team_id'][1].lower() if t.get('team_id') else ''
#             ticket_data = {
#                 'ticket_ref': t.get('ticket_ref', 'N/A'),
#                 'name': t.get('name', 'N/A'),
#                 'priority': t.get('priority', 'N/A'),
#                 'customer': t['partner_id'][1] if t.get('partner_id') else 'N/A',
#                 'assigned_to': t['user_id'][1] if t.get('user_id') else 'Unassigned',
#                 'stage': t['stage_id'][1] if t.get('stage_id') else 'N/A',
#                 'team': t['team_id'][1] if t.get('team_id') else 'N/A',
#                 'created': t.get('create_date', 'N/A'),
#                 'type': 'nautica' if "nautica" in team_name else 'home'
#             }

#             # Check if ticket already exists with the same ticket_ref and type
#             exists = db.exec(
#                 select(HelpdeskTicket).where(
#                     HelpdeskTicket.ticket_ref == ticket_data['ticket_ref'],
#                     HelpdeskTicket.type == ticket_data['type']
#                 )
#             ).first()
            
#             # Create a HelpdeskTicket instance and add to DB
#             if not exists:
#                 new_ticket = HelpdeskTicket(
#                     ticket_ref=ticket_data['ticket_ref'],
#                     name=ticket_data['name'],
#                     priority=ticket_data['priority'],
#                     customer=ticket_data['customer'],
#                     assigned_to=ticket_data['assigned_to'],
#                     stage=ticket_data['stage'],
#                     team=ticket_data['team'],
#                     created=ticket_data['created'],
#                     type=ticket_data['type']
#                 )
#                 db.add(new_ticket)
#                 count += 1

#         db.commit()
#         return JSONResponse(
#             content={
#                 "message": "Sync complete",
#                 "inserted": count
#             },
#             status_code=200
#         )
        
#     except Exception as e:
#         return JSONResponse(
#             content={"error": str(e)},
#             status_code=500
#         )



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
        for t in tickets:
            row = HelpdeskTicketNautica(  
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