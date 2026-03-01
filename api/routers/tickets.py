from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from fastapi.responses import JSONResponse
from fastapi import Query
import httpx
import pprint

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



def sync_tickets_home_from_odoo(db: Session) -> int:

    try:

        tickets = rpc_call(
            "helpdesk.ticket",
            "search_read",
            [[
                ("active", "=", True),
                ("team_id", "in", [5, 6]),
                ("stage_id.fold", "=", False),
            ]],
            {"fields": [
                "id", 
                "number", 
                "name", 
                "priority", 
                "stage_id", 
                "tag_ids", 
                "create_date", 
                "team_id",
                "partner_id",
                "partner_email",
                "user_id"
            ]}
        )

        # 1) find user email
        user_ids = sorted({t["user_id"][0] for t in tickets if t.get("user_id")})
        if user_ids:
            users = rpc_call(
                "res.users",
                "read",
                [user_ids],
                {"fields": ["id", "name", "login", "partner_id"]}
            )
            user_by_id = {u["id"]: u for u in users}
        # print(user_ids)
        # print(user_by_id)

        # create tickets
        nautica, home = [], []
        for t in tickets:

            # customer
            name = t["partner_id"][1] if t.get("partner_id") else "Unknown"
            email = t.get("partner_email") or "N/A"
            t["customer"] = f"{name}, {email}"

            # assigned to
            user_id = t.get("user_id")
            if user_id:
                u = user_by_id.get(user_id[0], {})
                t["assigned_to"] = u.get("name") + ", " + u.get("login")

            # split nautica & home
            tid = t["team_id"][0] if t.get("team_id") else None
            # if tid == 5: 
            #     nautica.append(t)
            if tid == 6:
                home.append(t)

        # print("NAUTICA:", len(nautica))
        # pprint.pprint(nautica)
        # print("\nHOME:", len(home))
        # pprint.pprint(home)

        # find existing refs 
        incoming_refs = [str(t.get("number") or "") for t in home]
        existing_refs = set()
        if incoming_refs:
            stmt = select(HelpdeskTicket.ticket_ref).where(HelpdeskTicket.ticket_ref.in_(incoming_refs))
            existing_refs = set(db.exec(stmt).all())
        # print('incoming_refs', incoming_refs)
        # print('existing refs', existing_refs)

        rows = []
        for t in home:
            ticket_ref = str(t.get("number") or "")
            if not ticket_ref:
                continue

            if ticket_ref in existing_refs:
                continue

            rows.append({
                "ticket_ref": ticket_ref,
                "name": (t.get("name") or ""),
                "priority": str(t.get("priority") or ""),
                "customer": (t.get("customer") or ""),
                "assigned_to": (t.get("assigned_to") or ""),
                "stage": (t["stage_id"][1] if t.get("stage_id") else ""),
                "team": "N/A",
                "created": (t.get("create_date") or ""),
                "type": "home",
                "completato": False,
            })

        if rows:
            db.bulk_insert_mappings(HelpdeskTicket, rows)
            db.commit()

        return {"inserted": len(rows)} 
           
    except Exception as e:
        raise
        



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
        return sync_tickets_home_from_odoo(db)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    # try:

    #     tickets = rpc_call(
    #         "helpdesk.ticket",
    #         "search_read",
    #         [[
    #             ("active", "=", True),
    #             ("team_id", "in", [5, 6]),
    #             ("stage_id.fold", "=", False),
    #         ]],
    #         {"fields": [
    #             "id", 
    #             "number", 
    #             "name", 
    #             "priority", 
    #             "stage_id", 
    #             "tag_ids", 
    #             "create_date", 
    #             "team_id",
    #             "partner_id",
    #             "partner_email",
    #             "user_id"
    #         ]}
    #     )

    #     # 1) find user email
    #     user_ids = sorted({t["user_id"][0] for t in tickets if t.get("user_id")})
    #     if user_ids:
    #         users = rpc_call(
    #             "res.users",
    #             "read",
    #             [user_ids],
    #             {"fields": ["id", "name", "login", "partner_id"]}
    #         )
    #         user_by_id = {u["id"]: u for u in users}
    #     # print(user_ids)
    #     # print(user_by_id)

    #     # create tickets
    #     nautica, home = [], []
    #     for t in tickets:

    #         # customer
    #         name = t["partner_id"][1] if t.get("partner_id") else "Unknown"
    #         email = t.get("partner_email") or "N/A"
    #         t["customer"] = f"{name}, {email}"

    #         # assigned to
    #         user_id = t.get("user_id")
    #         if user_id:
    #             u = user_by_id.get(user_id[0], {})
    #             t["assigned_to"] = u.get("name") + ", " + u.get("login")

    #         # split nautica & home
    #         tid = t["team_id"][0] if t.get("team_id") else None
    #         # if tid == 5: 
    #         #     nautica.append(t)
    #         if tid == 6:
    #             home.append(t)

    #     # print("NAUTICA:", len(nautica))
    #     # pprint.pprint(nautica)
    #     # print("\nHOME:", len(home))
    #     # pprint.pprint(home)

    #     # find existing refs 
    #     incoming_refs = [str(t.get("number") or "") for t in home]
    #     existing_refs = set()
    #     if incoming_refs:
    #         stmt = select(HelpdeskTicket.ticket_ref).where(HelpdeskTicket.ticket_ref.in_(incoming_refs))
    #         existing_refs = set(db.exec(stmt).all())
    #     # print('incoming_refs', incoming_refs)
    #     # print('existing refs', existing_refs)

    #     rows = []
    #     for t in home:
    #         ticket_ref = str(t.get("number") or "")
    #         if not ticket_ref:
    #             continue

    #         if ticket_ref in existing_refs:
    #             continue

    #         rows.append({
    #             "ticket_ref": ticket_ref,
    #             "name": (t.get("name") or ""),
    #             "priority": str(t.get("priority") or ""),
    #             "customer": (t.get("customer") or ""),
    #             "assigned_to": (t.get("assigned_to") or ""),
    #             "stage": (t["stage_id"][1] if t.get("stage_id") else ""),
    #             "team": "N/A",
    #             "created": (t.get("create_date") or ""),
    #             "type": "home",
    #             "completato": False,
    #         })

    #     if rows:
    #         db.bulk_insert_mappings(HelpdeskTicket, rows)
    #         db.commit()

    #     return {"inserted": len(rows)} 
           
    # except Exception as e:
    #     return JSONResponse(
    #         content={"error": str(e)},
    #         status_code=500
    #     )
        
