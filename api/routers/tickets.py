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

ODOO_URL="https://mulsp-odoo-1.worthtech.cloud"
ODOO_URL_LOGIN="https://mulsp-odoo-1.worthtech.cloud/web/login"
ODOO_URL_API="https://mulsp-odoo-1.worthtech.cloud/jsonrpc"
DB_NAME="odoodb_cleaned"
ODOO_BEARER_TOKEN="6c7beeefb78b508ac15f2ff430c4aa8e181b79bc"
WTH_FIREWALL_TOKEN="xt4GSYYeTKzMYfwGk4u5VYU"
PASSWORD_ODOO="6BIPI1m27ExErQk7H9bYvo"
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
            "helpdesk.ticket",
            "search",
            [[]]
        )
        print(ticket_ids)
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )