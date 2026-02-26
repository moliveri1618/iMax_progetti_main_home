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
from models.commesse import iCommesse
from models.users import iUsers
from schemas.commesse import ICommesseCreate, ICommesseRead, ICommesseUpdate
from models.workInProgress import WorkInProgress
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO
from pathlib import Path
import re
# log_file = Path(__file__).parent / "debug_output.txt"

router = APIRouter()

colonne = [
    "Elaborazione dati e SVILUPPO ",
    "Ordine a Fornitore",
    "Trasporto al cliente",
    "Trasporto al piano",
    "Smontaggio vecchio",
    "Taglio telai",
    "Posa serramento",
    "Rivestimento Interno",
    "Rilievo Misure",
    "Collaudo Finale"
    ]

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()

def get_props_for_code_category(code, product_templates):

    # find product id using name
    prod_ids = rpc_call(
        "product.product", "search",
        [[("default_code", "=", code)]],
    )
    if not prod_ids:
        print("No product.product found for", code)
        return False
    
    # get product categ id
    prod = rpc_call(
        "product.product", "read",
        [prod_ids],
        {"fields": ["id", "default_code", "product_tmpl_id", "categ_id"]}
    )[0]
    categ_id = prod["categ_id"][0]
    # print("VARIANT ID:", prod["id"])
    # print("TEMPLATE ID:", prod["product_tmpl_id"][0], "NAME:", prod["product_tmpl_id"][1])
    # print("CATEGORY:", prod["categ_id"][0], prod["categ_id"][1])

    # now get right template values for that category
    prop_map: dict[str, float] = {}
    for pt in product_templates:
        categ = pt.get("categ_id")
        if not categ or categ[0] != categ_id:
            continue
        #print("MATCHED TEMPLATE:", pt["id"], "CATEGORY:", categ)

        for p in pt.get("product_properties", []):
            key = normalize(p.get("string"))
            if not key:
                continue
            val = p.get("value")
            if val is False or val is None:
                val = 0.0
            prop_map[key] = float(val)

    #print(prop_map)
    return prop_map


def match_value(norm_col, prop_map):
    for key, value in prop_map.items():
        # exact match
        if norm_col == key:
            return value

        # partial match (both directions)
        if norm_col in key or key in norm_col:
            return value

    return None

# ODOO_URL="https://mulsp-odoo-1.worthtech.cloud"
# ODOO_URL_LOGIN="https://mulsp-odoo-1.worthtech.cloud/web/login"
# ODOO_URL_API="https://mulsp-odoo-1.worthtech.cloud/jsonrpc"
# DB_NAME="odoodb_cleaned"
# ODOO_BEARER_TOKEN="6c7beeefb78b508ac15f2ff430c4aa8e181b79bc"
# WTH_FIREWALL_TOKEN="xt4GSYYeTKzMYfwGk4u5VYU"
# UID = 2 
# TIMEOUT = 30.0
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


# Get all
@router.get("/all", response_model=List[ICommesseRead])
def read_commesse(db: Session = Depends(get_db)):
    commesse = db.exec(select(iCommesse)).all()
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
            
            statement = select(iCommesse).where(iCommesse.ordine == ordine_name)
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
                new_commessa = iCommesse(
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
                        work_item = WorkInProgress(
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
    # log_file.write_text("")  # ✅ clears file (rewrite)

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
                'x_studio_pagato_ok',
                'total_cost_of_lines',
                'total_recharge'
            ]}
        )
        #print(sale_orders)

        # get users emails 
        user_ids = list({
            order['user_id'][0]
            for order in sale_orders
            if order.get('user_id')
        })

        users = rpc_call(
            'res.users',
            'read',
            [user_ids],
            {'fields': ['id', 'name', 'login', 'email']}
        )
        user_info = {u['id']: u for u in users}


        
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

        # ✅ Step 3.1: Read product.template x_studio_imax
        template_ids = list({
            line['product_template_id'][0]
            for line in sale_order_lines
            if line.get('product_template_id')
        })

        # step 3.2: Get template details in batch
        product_templates = rpc_call(
            'product.template', 'read',
            [template_ids],
            {"fields": ["id", "x_studio_imax", "categ_id", "product_properties"]}
        )
        template_info = {pt['id']: pt for pt in product_templates}

        # Step 4: Gest product list as: 
        # i.e. 30: [LAVTENTAPINT] LAVORAZIONE TAPPEZZERIA INTERNA, [TENPACMOT] TENDA A PACCHETTO MOTORIZZATA
        order_to_products = defaultdict(list)
        for line in sale_order_lines:
            order_id = line['order_id'][0]

            # check for imax toggle yes/no
            if not line.get('product_template_id'):
                order_to_products[order_id].append({
                    "name": "No Product",
                    "x_studio_imax": None,
                })
                continue

            tmpl_id = line['product_template_id'][0]
            tmpl_name = line['product_template_id'][1]
            imax_value = template_info.get(tmpl_id, {}).get('x_studio_imax')

            order_to_products[order_id].append({
                "name": tmpl_name,
                "x_studio_imax": imax_value,
            })
        #print(order_to_products)
        
        # Step 5: Insert or skip commesse & products in DB
        inserted = 0
        for order in sale_orders:

            # ✅ only import iMax HOME
            if not (
                order.get("x_studio_imax_api") == "imax_home"
                and order.get("x_studio_costo_ok") is True
            ):
                continue
            
            #check if commessa exists in the db
            ordine_name = order.get('name')
            if not ordine_name:
                continue
            statement = select(iCommesse).where(iCommesse.ordine == ordine_name)
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

                # responsabile info in format: name, email
                user_id = order.get('user_id')[0] if order.get('user_id') else None
                user = user_info.get(user_id, {})
                user_name = user.get('name', 'N/A')
                user_email = user.get('login') or user.get('email') or 'N/A'
                responsabile_value = f"{user_name},{user_email}"
                
                #create new commessa
                new_commessa = iCommesse(
                    ordine=order['name'],  # Extract numbers only
                    data=datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date(),
                    nome_cliente = partner.get('name', 'N/A'),
                    email_cliente=partner.get('email', 'N/A'),
                    address_cliente=full_address,
                    responsabile=responsabile_value,
                    status=1 if order['invoice_status'] == 'to invoice' else 0,
                    costo=order.get('total_cost_of_lines', 0.0),
                    ricarico=order.get('total_recharge', 0.0),
                )
                db.add(new_commessa)
                db.flush() 
                # with open(log_file, "a", encoding="utf-8") as f:
                #     f.write(
                #         "[NEW COMMESSA INPUT]\n"
                #         f"  ordine: {order['name']}\n"
                #         f"  data: {datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date()}\n"
                #         f"  nome_cliente: {partner.get('name', 'N/A')}\n"
                #         f"  email_cliente: {partner.get('email', 'N/A')}\n"
                #         f"  address_cliente: {full_address}\n"
                #         f"  responsabile: {order['user_id'][1] if order.get('user_id') else 'N/A'}\n"
                #         f"  status: {1 if order.get('invoice_status') == 'to invoice' else 0}\n"
                # )
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
                code_cache = {}              
                for prod in products:
                    prod_name = prod["name"]
                    prod_imax = prod["x_studio_imax"]

                    # ✅ SKIP if False / None
                    if not prod_imax:
                        continue

                    match = re.match(r'\[(.*?)\]\s*(.*)', prod_name)  
                    if match:
                        code, desc = match.groups()
                    else:
                        code, desc = prod_name, ""

                    # ✅ find value rilievo misure etc for each product
                    if code not in code_cache:
                        code_cache[code] = get_props_for_code_category(code, product_templates)   

                    for col in colonne:
                        norm_col = normalize(col)
                        value = match_value(norm_col, code_cache[code])

                        work_item = WorkInProgress(
                            commesse_id=new_commessa.id,
                            zona=code,
                            modello=desc,
                            colonna=col,
                            completato=False,
                            completato_da_user="",
                            data_completamento=None,
                            valore=value
                        )
                        db.add(work_item)

                        # with open(log_file, "a", encoding="utf-8") as f:
                        #     f.write(
                        #         "[NEW WORK ITEM]\n"
                        #         f"  commesse_id: {new_commessa.id}\n"
                        #         f"  zona: {code}\n"
                        #         f"  modello: {desc}\n"
                        #         f"  colonna: {col}\n"
                        #         f"  x_studio_imax_api: {prod_imax}\n"
                        #         f"  completato: {False}\n"
                        #         f"  completato_da_user: {''}\n"
                        #         f"  data_completamento: {None}\n"
                        #         f"  valore: {value}\n"
                        #     )
                        # print(
                        #     "[NEW WORK ITEM]\n"
                        #     f"  commesse_id: {new_commessa.id}\n"
                        #     f"  zona: {code}\n"
                        #     f"  modello: {desc}\n"
                        #     f"  colonna: {col}\n"
                        #     f"  x_studio_imax_api: {prod_imax}\n"
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
@router.get("/{commessa_id}", response_model=ICommesseRead)
def read_commessa_by_id(commessa_id: int, db: Session = Depends(get_db)):
    commessa = db.get(iCommesse, commessa_id)
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
    commessa = db.get(iCommesse, commessa_id)
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
    commessa = db.get(iCommesse, commessa_id)
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

