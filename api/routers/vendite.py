from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Any, Dict, List, Optional
import sys, os
from xmlrpc import client
from collections import defaultdict
import re
from fastapi.responses import JSONResponse
from datetime import datetime

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.vendite import VenditeImax
from models.iConteggiCommessa import OrdiniPremi
from routers.utils import to_dict, to_month_str, default_vendite, _num
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO


router = APIRouter()

@router.get("/all")
def get_all_vendite(db: Session = Depends(get_db)):
    try:
        vendite_list = db.exec(select(VenditeImax)).all()
        return vendite_list
    except Exception as e:
        print(f"Error retrieving vendite: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving vendite from database.")


@router.get("/conteggi-commessa/{user_name}")
def get_conteggi_commessa_by_user(user_name: str, db: Session = Depends(get_db)):
    try:
        conteggi_list = db.exec(
            select(OrdiniPremi).where(OrdiniPremi.user_id == user_name)
        ).all()
        return conteggi_list
    except Exception as e:
        print(f"Error retrieving conteggi commessa for user {user_name}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conteggi commessa from database.")



@router.post("/odoo")
def get_vendite_from_odoo(
    db: Session = Depends(get_db),
    vendite: Optional[List[Dict[str, Any]]] = default_vendite
):

    ### TODO replace with real Odoo
    # # Connect to the common service and authenticate
    # models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')
    # common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
    # user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})
    
    # try:
    #     # Step 1: Get order lines
    #     sale_order_line_ids = models.execute_kw(
    #         DB_NAME_ODOO, user_id, PASSWORD_ODOO,
    #         'sale.order.line', 'search',
    #         [[['display_type', '=', False]]],
    #         {'limit': 50}
    #     )
        
    #     if not sale_order_line_ids:
    #         return JSONResponse(content={"message": "No sales orders found."}, status_code=404)


    #     sale_order_lines = models.execute_kw(
    #         DB_NAME_ODOO, user_id, PASSWORD_ODOO,
    #         'sale.order.line', 'read',
    #         [sale_order_line_ids],
    #         {'fields': [
    #             'order_id',
    #             'product_template_id',
    #             'name',
    #             'product_uom_qty',
    #             'price_unit',
    #             'cost_line_related',
    #             'recharge',
    #             'price_subtotal'
    #         ]}
    #     )

    #     # Step 2: Collect unique sale order IDs
    #     order_ids = list({line['order_id'][0] for line in sale_order_lines if line.get('order_id')})

    #     # Step 3: Fetch sale orders
    #     sale_orders = models.execute_kw(
    #         DB_NAME_ODOO, user_id, PASSWORD_ODOO,
    #         'sale.order', 'read',
    #         [order_ids],
    #         {'fields': ['id', 'name', 'user_id', 'team_id', 'partner_id', 'date_order']}
    #     )

    #     # Map by ID
    #     order_data = {order['id']: order for order in sale_orders}

    #     # Step 4: Display combined data
    #     inserted = 0
    #     for line in sale_order_lines:
    #         order = order_data.get(line['order_id'][0]) if line.get('order_id') else {}


    #         #check if ordine exists in the db
    #         ordine_name = order.get('name')
    #         if not ordine_name:
    #             continue
            
    #         statement = select(VenditeImax).where(VenditeImax.ordine == ordine_name)
    #         exists = db.exec(statement).first()
    #         if exists:
    #             continue  
            
            
    #         # Product
    #         product_raw = line['product_template_id'][1] if line.get('product_template_id') else 'N/A'
    #         match = re.match(r'\[(.*?)\]\s*(.*)', product_raw)
    #         if match:
    #             code_product, desc_product = match.groups()
    #             print(f"  Product: {code_product} | {desc_product}")
    #         else:
    #             code_product, desc_product = "N/A", product_raw
    #             #print(f"  Product: {product_raw}")
                
    #         # Description
    #         desc_raw = line['name']
    #         match = re.match(r'\[(.*?)\]\s*(.*)', desc_raw)
    #         if match:
    #             code, desc = match.groups()
    #             print(f"  Description: {code} | {desc}")
    #         else:
    #             code, desc = "N/A", desc_raw
    #             #print(f"  Description: {desc_raw}")
    #         try:
    #             vendite = VenditeImax(
    #                 ordine=order.get("name", "N/A"),
    #                 data=order.get("date_order"),
    #                 venditore=order["user_id"][1] if order.get("user_id") else "N/A",
    #                 team=order["team_id"][1] if order.get("team_id") else "N/A",
    #                 cliente=order["partner_id"][1] if order.get("partner_id") else "N/A",
    #                 prodotto=f"{code_product} | {desc_product}",
    #                 descrizione=f"{code} | {desc}",
    #                 quantita=line.get("product_uom_qty", 0),
    #                 prezzo_unitario=line.get("price_unit", 0),
    #                 costo_unitario=line.get("cost_line_related", 0),
    #                 ricarico=line.get("recharge", 0),
    #                 subtotale=line.get("price_subtotal", 0)
    #             )
    #             db.add(vendite)
    #             inserted += 1
                
    #         except Exception as inner_e:
    #             print(f"Skipping order {order.get('name')} due to error: {inner_e}")
                
    #         db.commit()
    #     return JSONResponse(content={"message": "Sync complete", "inserted": inserted}, status_code=200)
    # except Exception as e:
    #     print(f"Error fetching sale order lines: {e}")
    #     return JSONResponse(content={"error": str(e)}, status_code=500)

    # Map odoo data to VenditeImax model & insert into db 
    inserted = 0
    updated = 0

    for item in vendite:
        ordine = item["ordine_correlato"]

        existing = db.exec(
            select(VenditeImax).where(VenditeImax.ordine == ordine)
        ).first()

        if existing:
            # update fields
            existing.data = item["data_ordine"]
            existing.venditore = item["addetto_vendite"]
            existing.team = ""
            existing.cliente = item["cliente"]
            existing.prodotto = ""
            existing.descrizione = ""
            existing.quantita = 0
            existing.prezzo_unitario = 0
            existing.costo_unitario = item["prodotto_costo"]
            existing.ricarico = 0
            existing.subtotale = item["totale_imponibile"]
            updated += 1
        else:
            db.add(VenditeImax(
                ordine=ordine,
                data=item["data_ordine"],
                venditore=item["addetto_vendite"],
                team="",
                cliente=item["cliente"],
                prodotto="",
                descrizione="",
                quantita=0,
                prezzo_unitario=0,
                costo_unitario=item["prodotto_costo"],
                ricarico=0,
                subtotale=item["totale_imponibile"],
            ))
            inserted += 1

    db.commit()

    return {
        "message": "Upsert completed",
        "inserted": inserted,
        "updated": updated
    }


@router.get("/calculate-conteggi-commessa/{user_name}")
def get_conteggi_commessa(user_name: str, db: Session = Depends(get_db)):
    
    
    #1: return all VenditeImax records as a list of dictionaries
    try:
        query = select(VenditeImax).where(VenditeImax.venditore == user_name)
        vendite_list = db.exec(query).all()
        data = [to_dict(v) for v in vendite_list]
    except Exception as e:
        print(f"Error retrieving conteggi commessa for user {user_name}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conteggi commessa.")
    
    
    # 2 Perform calculations
    mapped: List[Dict[str, Any]] = []
    for row in data:
        venduto_a = _num(row.get("costo_unitario")) 
        acquistato_a = _num(row.get("subtotale"))  
        margine = venduto_a - acquistato_a
        
        mapped.append({
            "user_id": row.get("venditore"),
            "ordine_numero": row.get("ordine"),
            "cliente": row.get("cliente"),
            "prodotto": row.get("prodotto"),
            "mese": to_month_str(row.get("data")),
            "venduto_a": venduto_a,
            "costo_totale_acquisto": acquistato_a,
            "margine":margine,
            "percentuale_ricarico": (margine / acquistato_a * 100) if acquistato_a != 0 else None,
            # "percentuale_premio": None,
            # "valore_premio_lordo": None,
        })
    
    return data