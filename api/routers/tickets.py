from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from collections import defaultdict
import re
from fastapi.responses import JSONResponse
from datetime import datetime

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.tickets import HelpdeskTicket
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO

router = APIRouter()

@router.get("/odoo/tickets")
def fetch_helpdesk_tickets():
    
    # Connect to the common service and authenticate
    models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')
    common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
    user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})

    try:
        # 1. Search for tickets (no domain = fetch all)
        ticket_ids = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'helpdesk.ticket', 'search',
            [[]]
        )

        # 2. Read ticket data
        tickets = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'helpdesk.ticket', 'read',
            [ticket_ids],
            {'fields': [
                'ticket_ref',
                'name',
                'priority',
                'partner_id',
                'user_id',
                'stage_id',
                'team_id',
                'create_date',
            ]}
        )

        result = []

        # 3. Build unified ticket list with "type"
        for t in tickets:
            team_name = t['team_id'][1].lower() if t.get('team_id') else ''
            ticket_data = {
                'ticket_ref': t.get('ticket_ref', 'N/A'),
                'name': t.get('name', 'N/A'),
                'priority': t.get('priority', 'N/A'),
                'customer': t['partner_id'][1] if t.get('partner_id') else 'N/A',
                'assigned_to': t['user_id'][1] if t.get('user_id') else 'Unassigned',
                'stage': t['stage_id'][1] if t.get('stage_id') else 'N/A',
                'team': t['team_id'][1] if t.get('team_id') else 'N/A',
                'created': t.get('create_date', 'N/A'),
                'type': 'nautica' if "nautica" in team_name else 'home'
            }
            result.append(ticket_data)

        # 4. Return the unified result list
        return JSONResponse(content={"tickets": result}, status_code=200)

    except Exception as e:
        print(f"Error fetching helpdesk tickets: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


