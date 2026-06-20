from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from collections import defaultdict
import re
from fastapi.responses import JSONResponse
from datetime import datetime
import httpx
from sqlalchemy import text
import pprint
from pathlib import Path

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.commesseNautica import iCommesseNautica
from models.users import iUsers
from schemas.commesseNautica import ICommesseNauticaRead
from models.workInProgressNautica import WorkInProgressNautica
from dependecies import get_db
# log_file = Path(__file__).parent / "debug_output.txt"

router = APIRouter()


colonne = [
    "Rilievo Misure",
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
    "GUIDE e Floggiatura",
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

COMMESSE_HOME_LOCK_ID = 1002

def try_acquire_lock(db: Session, lock_id: int) -> bool:
    result = (
        db.connection()
        .execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": lock_id},
        )
        .scalar()
    )
    return bool(result)


def release_lock(db: Session, lock_id: int) -> None:
    db.connection().execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": lock_id},
    )


ODOO_URL="https://odoo.mulattieri.it"
ODOO_URL_LOGIN="https://odoo.mulattieri.it/web/login"
ODOO_URL_API="https://odoo.mulattieri.it/jsonrpc"
DB_NAME="mulsp-odoo-production"
ODOO_BEARER_TOKEN="ocCAF0fVHguW3O*CbTRd*3v9"
WTH_FIREWALL_TOKEN="SK9L6EV4WM934L8YV10HWRE0D5Q6JIG7CF0NGFPWICYCFEKZD58XEIWG2P77"
UID = 85
TIMEOUT = 30.0
ODOO_CONTEXT = {
    "lang": "it_IT",
    "tz": "Europe/Rome",
}

def rpc_call(model, method, args=None, kwargs=None):

    if kwargs is None:
        kwargs = {}


    # merge default global context with per-call context
    kwargs["context"] = {
        **ODOO_CONTEXT,
        **kwargs.get("context", {})
    }


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

def commesse_updates(sale_orders, existing_map):
    updates = []

    for order in sale_orders:
        ordine = order.get("name")
        existing_row = existing_map.get(ordine)

        if not existing_row:
            continue

        new_costo_ok = order.get("x_studio_costo_ok")
        new_data_costo_ok = (
            datetime.strptime(order["costo_ok_timestamp"], "%Y-%m-%d %H:%M:%S")
            if order.get("costo_ok_timestamp")
            else None
        )
        new_costo = order.get("amount_untaxed", 0.0)
        new_ricarico = order.get("total_cost_of_lines", 0.0)

        old_costo_ok = existing_row["costo_ok"]
        old_data_costo_ok = existing_row["data_costo_ok"]
        old_costo = existing_row["costo"]
        old_ricarico = existing_row["ricarico"]

        if (
            old_costo_ok != new_costo_ok
            or old_data_costo_ok != new_data_costo_ok
            or old_costo != new_costo
            or old_ricarico != new_ricarico
        ):
            updates.append(
                {
                    "id": existing_row["id"],
                    "costo_ok": new_costo_ok,
                    "data_costo_ok": new_data_costo_ok,
                    "costo": new_costo,
                    "ricarico": new_ricarico,
                }
            )

    return updates

def sync_commesse_nautica_odoo(db: Session) -> int:
    try:

        # Get all projects
        sale_orders = rpc_call(
            "sale.order", "search_read",
            [[
                ["state", "!=", "cancel"],
                ["x_studio_imax_api", "=", "imax_nautica"],
                ["state", "=", "sale"],
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
                    "costo_ok_timestamp",
                    "x_studio_pagato_ok",
                    "amount_untaxed",
                    "total_cost_of_lines",
                    "state"
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
        print("Sale orders:")
        pprint.pprint(sale_orders)
        # print("Extracted sale order IDs:")
        # pprint.pprint(sale_order_ids)
        # print("Odoo ordini:")
        # pprint.pprint(odoo_ordini)
        # with open(log_file, "w", encoding="utf-8") as f:
        #     f.write("SALE ORDERS\n")
        #     f.write("=" * 80 + "\n\n")

        #     for order in sale_orders:
        #         f.write(f"ID: {order.get('id')}\n")
        #         f.write(f"Name: {order.get('name')}\n")
        #         f.write(f"Date: {order.get('date_order')}\n")
        #         f.write(f"Partner: {order.get('partner_id')}\n")
        #         f.write(f"User: {order.get('user_id')}\n")
        #         f.write(f"Amount total: {order.get('amount_total')}\n")
        #         f.write(f"Invoice status: {order.get('invoice_status')}\n")
        #         f.write(f"x_studio_imax_api: {order.get('x_studio_imax_api')}\n")
        #         f.write(f"x_studio_costo_ok: {order.get('x_studio_costo_ok')}\n")
        #         f.write(f"x_studio_pagato_ok: {order.get('x_studio_pagato_ok')}\n")
        #         f.write(f"total_cost_of_lines: {order.get('total_cost_of_lines')}\n")
        #         f.write(f"total_recharge: {order.get('total_recharge')}\n")
        #         f.write("-" * 80 + "\n")

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
            "sale.order.line",
            "search_read",
            [
                [
                    ["order_id", "in", sale_order_ids],
                    ["product_template_id", "!=", False],
                    ["product_template_id.x_studio_imax", "=", True],
                ]
            ],
            {"fields": ["order_id", "product_template_id", "x_studio_pos"]},
        )
        order_to_products_mapping = defaultdict(list)
        template_ids_set = set()
        for line in sale_order_products:
            order_id_data = line.get("order_id")
            tmpl_data = line.get("product_template_id")

            if not order_id_data or not tmpl_data:
                continue

            order_id = order_id_data[0]
            tmpl_id, tmpl_name = tmpl_data
            template_ids_set.add(tmpl_id)

            order_to_products_mapping[order_id].append(
                (tmpl_id, tmpl_name, line.get("x_studio_pos") or "")
            )
        template_ids = list(template_ids_set)
        # print("Sale order products:")
        # pprint.pprint(sale_order_products)
        # print("Order to products mapping:")
        # pprint.pprint(order_to_products_mapping)

        CODE_RE = re.compile(r"\[(.*?)\]\s*(.*)")
        COLS_NORM = [(col, normalize(col)) for col in colonne]
        # print("Columns to match:", CODE_RE)
        # print("Normalized columns:", COLS_NORM)

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
                if v is None or v is False:
                    v = 0.0
                prop_map[k] = float(v)
            template_props_map[t["id"]] = prop_map
        # print("Template properties map:")
        # pprint.pprint(template_props_map)

        # Fetch existing ordini in ONE query & determine which orders are new
        # existing = db.exec(
        #     select(iCommesseNautica.ordine).where(iCommesseNautica.ordine.in_(odoo_ordini))
        # ).all()
        # existing_set = set(existing)
        existing = db.exec(
            select(
                iCommesseNautica.id,
                iCommesseNautica.ordine,
                iCommesseNautica.costo_ok,
                iCommesseNautica.data_costo_ok,
                iCommesseNautica.costo,
                iCommesseNautica.ricarico,
            ).where(iCommesseNautica.ordine.in_(odoo_ordini))
        ).all()

        existing_map = {
            row.ordine: {
                "id": row.id,
                "costo_ok": row.costo_ok,
                "data_costo_ok": row.data_costo_ok,
                "costo": row.costo,
                "ricarico": row.ricarico,
            }
            for row in existing
        }
        updates= commesse_updates(sale_orders, existing_map)
        if updates :
            db.bulk_update_mappings(iCommesseNautica, updates)

        existing_set = set(existing_map.keys())
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

            # create new commessa
            new_commessa = iCommesseNautica(
                ordine=order["name"],  # Extract numbers only
                data=datetime.strptime(order["date_order"], "%Y-%m-%d %H:%M:%S").date(),
                nome_cliente=partner.get("name") or None,
                email_cliente=partner.get("email") or None,
                address_cliente=address_cliente,
                costo_ok=order.get("x_studio_costo_ok"),
                data_costo_ok=datetime.strptime(order["costo_ok_timestamp"], "%Y-%m-%d %H:%M:%S") if order.get("costo_ok_timestamp") else None,
                responsabile=responsabile_value,
                status=0,
                costo=order.get("amount_untaxed", 0.0),
                ricarico=order.get("total_cost_of_lines", 0.0),
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
        db.flush()  # ✅ one flush for all commesse (ids assigned)

        # add products to the new commessa
        work_items = []
        append_work_item = work_items.append

        for order in new_orders:
            commessa = commesse_by_order_id[order["id"]]
            products = order_to_products_mapping.get(order["id"], [])

            for tmpl_id, tmpl_name, posizione in products:
                m = CODE_RE.match(tmpl_name)
                if m:
                    code, desc = m.groups()
                else:
                    code, desc = tmpl_name, ""

                props = template_props_map.get(tmpl_id, {})
                for col, norm_col in COLS_NORM:
                    append_work_item(
                        {
                            "commesse_id": commessa.id,
                            "zona": code,
                            "modello": posizione,
                            "colonna": col,
                            "completato": False,
                            "completato_da_user": "",
                            "data_completamento": None,
                            "valore": match_value(norm_col, props),
                        }
                    )
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
            db.bulk_insert_mappings(WorkInProgressNautica, work_items[i:i+CHUNK])

        db.commit()
        return len(commesse_to_add)

    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        raise


# Get all
@router.get("/all", response_model=List[ICommesseNauticaRead])
def read_commesse(db: Session = Depends(get_db)):
    commesse = db.exec(select(iCommesseNautica)).all()
    return commesse


# from odoo
@router.post("/odoo/v2")
def get_commesse_from_odoo(db: Session = Depends(get_db)):

    acquired = try_acquire_lock(db, COMMESSE_HOME_LOCK_ID)
    if not acquired:
        raise HTTPException(status_code=409, detail="Sync already running")

    try:
        return sync_commesse_nautica_odoo(db)
    except Exception as e:
        db.rollback()
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        release_lock(db, COMMESSE_HOME_LOCK_ID)


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
