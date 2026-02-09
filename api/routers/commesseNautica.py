from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from collections import defaultdict
import re
from fastapi.responses import JSONResponse
from datetime import datetime
import httpx
import pprint
from pathlib import Path

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.commesseNautica import iCommesseNautica
from models.users import iUsers
from schemas.commesseNautica import ICommesseNauticaRead
from models.workInProgressNautica import WorkInProgressNautica
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO

router = APIRouter()



colonne = [
    "Rilievo misure",
    "ORDINE e Sviluppo Progetto",
    "Taglio Binario",
    "Binario Assemblato",
    "TAGLIO TESS Sartoria",
    "Confezione Sartoria",
    "Lavorazioni EXTRA Sartoria",
    "Taglio tessuto TECNICO + lavorazioni",
    "Bin + Tess. Ass. + imballo",
    "Montaggio Attacchi",
    "Scarico Trasporto al piano",
    "Montaggio Tenda",
    "GUIDE e Floggiatura"
]


ODOO_URL="https://odoo.mulattieri.it"
ODOO_URL_LOGIN="https://odoo.mulattieri.it/web/login"
ODOO_URL_API="https://odoo.mulattieri.it/jsonrpc"
DB_NAME="mulsp-odoo-production"
ODOO_BEARER_TOKEN="ocCAF0fVHguW3O*CbTRd*3v9"
WTH_FIREWALL_TOKEN="SK9L6EV4WM934L8YV10HWRE0D5Q6JIG7CF0NGFPWICYCFEKZD58XEIWG2P77"
UID = 85
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


# Get all
@router.get("/all", response_model=List[ICommesseNauticaRead])
def read_commesse(db: Session = Depends(get_db)):
    commesse = db.exec(select(iCommesseNautica)).all()
    return commesse

@router.get("/odoo")
def get_commesse_from_odoo(db: Session = Depends(get_db)):
        
    # Connect to the common service and authenticate
    models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')
    common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
    user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})
    
    try:
        # Step 1: Search for sale order IDs
        sale_order_ids = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'search',
            [[['state', '!=', 'cancel']]],
        )
        print(sale_order_ids)

        if not sale_order_ids:
            return JSONResponse(content={"message": "No sales orders found."}, status_code=404)


        # Step 2: Read sale order data
        sale_orders = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'read',
            [sale_order_ids],
            {'fields': [
                'name',            
                'date_order',      
                'partner_id',      
                'user_id',         
                'activity_ids',    
                'total_cost_of_lines',
                'total_recharge',
                'amount_total',
                'invoice_status',
            ]}
        )
        
        # Step 2.1: Read partners (client) data
        partner_ids = list({order['partner_id'][0] for order in sale_orders if order.get('partner_id')})
        partners = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'res.partner', 'read',
            [partner_ids],
            {'fields': ['id', 'name', 'email', 'street', 'city', 'zip', 'country_id']}
        )
        partner_info = {p['id']: p for p in partners}

        # Step 3: Fetch related sale order lines
        sale_order_line_ids = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order.line', 'search',
            [[['order_id', 'in', sale_order_ids]]]
        )

        sale_order_lines = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order.line', 'read',
            [sale_order_line_ids],
            {'fields': ['order_id', 'product_template_id']}
        )

        # Step 4: Group products by order
        order_to_products = defaultdict(list)
        for line in sale_order_lines:
            order_id = line['order_id'][0]
            product_name = line['product_template_id'][1] if line['product_template_id'] else "No Product"
            order_to_products[order_id].append(product_name)

        # Step 5: Display everything
        inserted = 0
        for order in sale_orders:
            
            #check if ordine exists in the db
            ordine_name = order.get('name')
            if not ordine_name:
                continue

            statement = select(iCommesseNautica).where(iCommesseNautica.ordine == ordine_name)
            exists = db.exec(statement).first()
            if exists:
                continue 
            
            try:
                
                # Partner info
                partner_id = order.get('partner_id')[0] if order.get('partner_id') else None
                partner = partner_info.get(partner_id, {})
                address_parts = [
                    partner.get('street', ''),
                    partner.get('city', ''),
                    partner.get('zip', ''),
                    partner.get('country_id', ['', ''])[1] if partner.get('country_id') else ''
                ]
                full_address = ', '.join(part for part in address_parts if part).strip(', ')

                #create new commessa
                new_commessa = iCommesseNautica(
                    ordine=order['name'],  # Extract numbers only
                    data=datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date(),
                    nome_cliente = partner.get('name', 'N/A'),
                    email_cliente=partner.get('email', 'N/A'),
                    address_cliente=full_address,
                    responsabile=order['user_id'][1] if order['user_id'] else "N/A",
                    status=1 if order['invoice_status'] == 'to invoice' else 0
                )
                
                db.add(new_commessa)
                db.flush() 
                
                # Add products to the new commessa
                products = order_to_products.get(order['id'], [])
                # print("  Products:")
                
                for prod in products:
                    match = re.match(r'\[(.*?)\]\s*(.*)', prod)
                    if match:
                        code, desc = match.groups()
                        # print(f"    - {code} | {desc}")
                    else:
                        code, desc = prod, ""
                        # print(f"    - {prod}")
                        
                    for col in colonne:
                        print('hrer')
                        work_item = WorkInProgressNautica(
                            commesse_id=new_commessa.id,
                            zona=code,
                            modello=desc,
                            colonna=col,
                            completato=False,
                            completato_da_user="",
                            data_completamento=None
                        )
                        db.add(work_item)
                
                db.commit()
                inserted += 1

            except Exception as inner_e:
                db.rollback()
                print(f"Skipping order {order.get('name')} due to error: {inner_e}")
                
                    
        return JSONResponse(content={"message": "Sync complete", "inserted": inserted}, status_code=200)

    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/odoo/v2")
def get_commesse_from_odoo(db: Session = Depends(get_db)):
    
    try:
        
        # Step 1: Search for sale order IDs
        sale_order_ids = rpc_call(
            'sale.order','search',
            [[['state', '!=', 'cancel']]],
        )
        if not sale_order_ids:
            return JSONResponse(content={"message": "No sales orders found."}, status_code=404)
        #print(sale_order_ids)
        
        # Step 2: Read sale order data (RPC)
        sale_orders = rpc_call(
            'sale.order', 'read',
            [sale_order_ids],
            {'fields': [
                'name',
                'date_order',
                'partner_id',
                'user_id',
                'activity_ids',
                'amount_total',
                'invoice_status',
                'x_studio_imax_api',
                'x_studio_costo_ok',
                'x_studio_pagato_ok'
            ]}
        )
        #print(sale_orders)
        
        # Step 2.1: Read partners (client) data (RPC)
        partner_ids = list({order['partner_id'][0] for order in sale_orders if order.get('partner_id')})
        partners = rpc_call(
            'res.partner', 'read',
            [partner_ids],
            {'fields': [
                'id', 
                'name', 
                'email', 
                'street', 
                'city', 
                'zip', 
                'country_id'
            ]}
        )
        partner_info = {p['id']: p for p in partners}
        # print(partners)
        # print(partner_info)    
        
        # Step 3: Fetch related sale order lines (RPC)
        sale_order_line_ids = rpc_call(
            'sale.order.line', 'search',
            [[['order_id', 'in', sale_order_ids]]]
        )
        sale_order_lines = rpc_call(
            'sale.order.line', 'read',
            [sale_order_line_ids],
            {'fields': ['order_id', 'product_template_id']}
        )
        #print(sale_order_lines)
        
        # Step 4: Gest product list as: 
        #           30: [LAVTENTAPINT] LAVORAZIONE TAPPEZZERIA INTERNA, [TENPACMOT] TENDA A PACCHETTO MOTORIZZATA
        order_to_products = defaultdict(list)
        for line in sale_order_lines:
            order_id = line['order_id'][0]
            product_name = line['product_template_id'][1] if line['product_template_id'] else "No Product"
            order_to_products[order_id].append(product_name)
        #print(order_to_products)
        
        # Step 5: Insert or skip commesse & products in DB
        inserted = 0
        for order in sale_orders:

            # only import iMax HOME
            if not (
                order.get("x_studio_imax_api") == "imax_nautica"
                and order.get("x_studio_costo_ok") is True
            ):
                continue
            
            #check if commessa exists in the db
            ordine_name = order.get('name')
            if not ordine_name:
                continue
            statement = select(iCommesseNautica).where(iCommesseNautica.ordine == ordine_name)
            exists = db.exec(statement).first()
            if exists:
                continue 
            
            # insert new commessa & products
            try:
                
                # client info
                partner_id = order.get('partner_id')[0] if order.get('partner_id') else None
                partner = partner_info.get(partner_id, {})
                address_parts = [
                    partner.get('street', ''),
                    partner.get('city', ''),
                    partner.get('zip', ''),
                    partner.get('country_id', ['', ''])[1] if partner.get('country_id') else ''
                ]
                full_address = ', '.join(part for part in address_parts if part).strip(', ')
                
                #create new commessa
                new_commessa = iCommesseNautica(
                    ordine=order['name'],  # Extract numbers only
                    data=datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date(),
                    nome_cliente = partner.get('name', 'N/A'),
                    email_cliente=partner.get('email', 'N/A'),
                    address_cliente=full_address,
                    responsabile=order['user_id'][1] if order['user_id'] else "N/A",
                    status=1 if order['invoice_status'] == 'to invoice' else 0
                )
                db.add(new_commessa)
                db.flush() 
                # print(
                #     "[NEW COMMESSA INPUT]\n"
                #     f"  ordine: {order['name']}\n"
                #     f"  data: {datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date()}\n"
                #     f"  nome_cliente: {partner.get('name', 'N/A')}\n"
                #     f"  email_cliente: {partner.get('email', 'N/A')}\n"
                #     f"  address_cliente: {full_address}\n"
                #     f"  responsabile: {order['user_id'][1] if order.get('user_id') else 'N/A'}\n"
                #     f"  status: {1 if order.get('invoice_status') == 'to invoice' else 0}\n"
                # )
                
                
                # Add products to the new commessa
                products = order_to_products.get(order['id'], [])                
                for prod in products:
                    match = re.match(r'\[(.*?)\]\s*(.*)', prod)
                    if match:
                        code, desc = match.groups()
                    else:
                        code, desc = prod, ""                        
                    for col in colonne:
                        work_item = WorkInProgressNautica(
                            commesse_id=new_commessa.id,
                            zona=code,
                            modello=desc,
                            colonna=col,
                            completato=False,
                            completato_da_user="",
                            data_completamento=None
                        )
                        db.add(work_item)

                        # print(
                        #     "[NEW WORK ITEM]\n"
                        #     # f"  commesse_id: {new_commessa.id}\n"
                        #     f"  zona: {code}\n"
                        #     f"  modello: {desc}\n"
                        #     f"  colonna: {col}\n"
                        #     f"  completato: {False}\n"
                        #     f"  completato_da_user: {''}\n"
                        #     f"  data_completamento: {None}\n"
                        # )
                
                db.commit()
                inserted += 1

            except Exception as inner_e:
                db.rollback()
                print(f"Skipping order {order.get('name')} due to error: {inner_e}")
        
    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    return inserted


# Get one commessa by ID
@router.get("/{commessa_id}", response_model=ICommesseNauticaRead)
def read_commessa_by_id(commessa_id: int, db: Session = Depends(get_db)):
    commessa = db.get(iCommesseNautica, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")
    

    # Fetch users by the IDs
    user_ids = commessa.assignedUserIds or []
    users = db.query(iUsers).filter(iUsers.id.in_(user_ids)).all()
    assigned_users_list = [{"id": u.id, "name": u.name} for u in users]

    return {
        **commessa.__dict__,
        "_sa_instance_state": None,
        "assignedUsers": assigned_users_list
    }


@router.put("/update_column/{commessa_id}")
def update_commessa_column(
    commessa_id: int,
    column_name: str,
    column_value: str,
    db: Session = Depends(get_db),
):
    commessa = db.get(iCommesseNautica, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")

    if not hasattr(commessa, column_name):
        raise HTTPException(status_code=400, detail=f"Invalid column name: {column_name}")

    setattr(commessa, column_name, column_value)
    db.add(commessa)
    db.commit()
    db.refresh(commessa)

    return {"message": "Column updated successfully", "updated": {column_name: column_value}}


@router.put("/update_assignedUserIds/{commessa_id}")
def update_commessa_assigned_users(
    commessa_id: int,
    assignedUserIds: List[int],          
    db: Session = Depends(get_db),
):
    commessa = db.get(iCommesseNautica, commessa_id)
    if not commessa:
        raise HTTPException(status_code=404, detail="Commessa not found")

    # assign list of ints directly
    commessa.assignedUserIds = assignedUserIds

    db.add(commessa)
    db.commit()
    db.refresh(commessa)

    return {
        "message": "assignedUserIds updated successfully",
        "assignedUserIds": commessa.assignedUserIds,
    }

