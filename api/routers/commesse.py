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


@router.get("/odoo/v2")
def get_commesse_from_odoo(db: Session = Depends(get_db)):
    # log_file.write_text("")  # ✅ clears file (rewrite)

    try:
        
        # Get all projects
        sale_orders = rpc_call(
            "sale.order", "search_read",
            [[
                ["state", "!=", "cancel"],
                ["x_studio_imax_api", "=", "imax_home"],
                ["x_studio_costo_ok", "=", True],
            ]],
            {
                "fields": [
                    "id",  
                    "name",
                    "date_order",
                    "partner_id",
                    "user_id",
                    "activity_ids",
                    "amount_total",
                    "invoice_status",
                    "x_studio_imax_api",
                    "x_studio_costo_ok",
                    "x_studio_pagato_ok",
                    "total_cost_of_lines",
                    "total_recharge",
                ]
            }
        )
        sale_order_ids = []
        odoo_ordini = set()
        for o in sale_orders:
            if o.get("id"):
                sale_order_ids.append(o["id"])
            if o.get("name"):
                odoo_ordini.add(o["name"])
        # print("Sale orders:")
        # pprint.pprint(sale_orders)
        # print("Extracted sale order IDs:")
        # pprint.pprint(sale_order_ids)
        # print("Odoo ordini:")
        # pprint.pprint(odoo_ordini)

        # Get fetch users 
        user_ids = list({o["user_id"][0] for o in sale_orders if o.get("user_id")})
        users = rpc_call(
            "res.users", "read",
            [user_ids],
            {"fields": ["id", "name", "login", "email"]}
        )
        user_info = {u["id"]: u for u in users}
        # print("Users info:")
        # pprint.pprint(user_info)

        # Get clients
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
        partner_info = {p['id']: p for p in partners} # convert to dict, faster
        # print('Partners:')
        # pprint.pprint(partners)
        # print('Partner info:')
        # pprint.pprint(partner_info)    


        sale_order_products = rpc_call(
            "sale.order.line", "search_read",
            [[
                ["order_id", "in", sale_order_ids],
                ["product_template_id", "!=", False],  
                ["product_template_id.x_studio_imax", "=", True]
            ]],
            {"fields": ["order_id", "product_template_id"]}
        )
        order_to_products_mapping = defaultdict(dict)
        for line in sale_order_products:
            order_id = line["order_id"][0]
            tmpl_id, tmpl_name = line["product_template_id"]
            order_to_products_mapping[order_id][tmpl_id] = tmpl_name
        # print("Sale order products:")
        # pprint.pprint(sale_order_products)
        # print("Order to products mapping:")
        # pprint.pprint(order_to_products_mapping)

        CODE_RE = re.compile(r"\[(.*?)\]\s*(.*)")
        COLS_NORM = [(col, normalize(col)) for col in colonne]
        # print("Columns to match:", CODE_RE)
        # print("Normalized columns:", COLS_NORM)

        template_ids = list({
            tmpl_id
            for products_by_tmpl in order_to_products_mapping.values()
            for tmpl_id in products_by_tmpl.keys()
        })
        templates = rpc_call(
            "product.template", "read",
            [template_ids],
            {"fields": ["id", "product_properties"]}
        )
        template_props_map: dict[int, dict[str, float]] = {}
        for t in templates:
            prop_map: dict[str, float] = {}
            for p in t.get("product_properties", []):
                k = normalize(p.get("string"))
                if not k:
                    continue
                v = p.get("value")
                if v is False or v is None:
                    v = 0.0
                prop_map[k] = float(v)
            template_props_map[t["id"]] = prop_map
        # print("Template properties map:")
        # pprint.pprint(template_props_map)

        # Fetch existing ordini in ONE query
        existing = db.exec(
            select(iCommesse.ordine).where(iCommesse.ordine.in_(odoo_ordini))
        ).all()
        existing_set = set(existing)
        new_orders = [o for o in sale_orders if o.get("name") not in existing_set]
        # print('existing ordini in DB:', existing_set)
        # print('new_orders', new_orders)

        # Insert or skip commesse & products in DB
        commesse_by_order_id = {}
        commesse_to_add = []
        for order in new_orders:

            # user info
            user_id = order["user_id"][0]
            user = user_info.get(user_id, {})
            user_name = order["user_id"][1] 
            user_email = user.get("login") or ""
            responsabile_value = f"{user_name},{user_email}"

            # partner info
            partner_id = order["partner_id"][0] 
            partner = partner_info.get(partner_id, {})
            city = partner.get("city")
            zip_code = partner.get("zip") 
            country_id = partner.get("country_id") or [None, None]
            country = country_id[1] if len(country_id) > 1 else None
            address_cliente = ", ".join([p for p in [city, zip_code, country] if p])

            #create new commessa
            new_commessa = iCommesse(
                ordine=order['name'],  # Extract numbers only
                data=datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date(),
                nome_cliente = partner.get('name', 'N/A'),
                email_cliente=partner.get('email', 'N/A'),
                address_cliente=address_cliente,
                responsabile=responsabile_value,
                status=0,
                costo=order.get('total_cost_of_lines', 0.0),
                ricarico=order.get('total_recharge', 0.0),
            )
            # with open(log_file, "a", encoding="utf-8") as f:
            #     f.write(
            #         "[NEW COMMESSA INPUT]\n"
            #         f"  ordine: {order['name']}\n"
            #         f"  data: {datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S').date()}\n"
            #         f"  nome_cliente: {partner.get('name', 'N/A')}\n"
            #         f"  email_cliente: {partner.get('email', 'N/A')}\n"
            #         f"  address_cliente: {address_cliente}\n"
            #         f"  responsabile: {responsabile_value}\n"
            #         f"  status: {0}\n"
            # )
            commesse_to_add.append(new_commessa)
            commesse_by_order_id[order["id"]] = new_commessa

        db.add_all(commesse_to_add)
        db.flush() 

        # add products to the new commessa
        work_items = []
        for order in new_orders:
            commessa = commesse_by_order_id[order["id"]]
            products = order_to_products_mapping.get(order["id"], {})

            for tmpl_id, tmpl_name in products.items():

                # extract code: [LAVTENTAPINT], desc: LAVORAZIONE TAPPEZZERIA INTERNA
                m = CODE_RE.match(tmpl_name)
                if m:
                    code, desc = m.groups() 
                else:
                    code, desc = tmpl_name, ""

                props = template_props_map.get(tmpl_id, {}) # get activities values for that product template
                for col, norm_col in COLS_NORM:
                    value = match_value(norm_col, props) # match activities from odoo with colonne.to_lower()

                    work_items.append({
                        "commesse_id": commessa.id,
                        "zona": code,
                        "modello": desc,
                        "colonna": col,
                        "completato": False,
                        "completato_da_user": "",
                        "data_completamento": None,
                        "valore": value,
                    })
                    # with open(log_file, "a", encoding="utf-8") as f:
                    #     f.write(
                    #         "[NEW PRODUCT]\n"
                    #         f"  commesse_id: {new_commessa.id}\n"
                    #         f"  zona: {code}\n"
                    #         f"  modello: {desc}\n"
                    #         f"  colonna: {col}\n"
                    #         f"  x_studio_imax_api: {prod.get('x_studio_imax')}\n"
                    #         f"  completato: {False}\n"
                    #         f"  completato_da_user: {''}\n"
                    #         f"  data_completamento: {None}\n"
                    #         f"  valore: {value}\n"
                    # )

        # If this list can be huge, insert in chunks
        CHUNK = 5000
        for i in range(0, len(work_items), CHUNK):
            db.bulk_insert_mappings(WorkInProgress, work_items[i:i+CHUNK])

        db.commit()
        return len(commesse_to_add)

    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)



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

