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
from models.vendite import VenditeImax
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO


router = APIRouter()

@router.get("")
def get_all_vendite(db: Session = Depends(get_db)):
    try:
        vendite_list = db.exec(select(VenditeImax)).all()
        return vendite_list
    except Exception as e:
        print(f"Error retrieving vendite: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving vendite from database.")



@router.get("/odoo/")
def get_vendite_from_odoo(db: Session = Depends(get_db)):
    
    # Connect to the common service and authenticate
    models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')
    common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
    user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})
    
    try:
        # Step 1: Get order lines
        sale_order_line_ids = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order.line', 'search',
            [[['display_type', '=', False]]],
            {'limit': 50}
        )
        
        if not sale_order_line_ids:
            return JSONResponse(content={"message": "No sales orders found."}, status_code=404)


        sale_order_lines = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order.line', 'read',
            [sale_order_line_ids],
            {'fields': [
                'order_id',
                'product_template_id',
                'name',
                'product_uom_qty',
                'price_unit',
                'cost_line_related',
                'recharge',
                'price_subtotal'
            ]}
        )

        # Step 2: Collect unique sale order IDs
        order_ids = list({line['order_id'][0] for line in sale_order_lines if line.get('order_id')})

        # Step 3: Fetch sale orders
        sale_orders = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'read',
            [order_ids],
            {'fields': ['id', 'name', 'user_id', 'team_id', 'partner_id', 'date_order']}
        )

        # Map by ID
        order_data = {order['id']: order for order in sale_orders}

        # Step 4: Display combined data
        inserted = 0
        for line in sale_order_lines:
            order = order_data.get(line['order_id'][0]) if line.get('order_id') else {}


            #check if ordine exists in the db
            ordine_name = order.get('name')
            if not ordine_name:
                continue
            
            statement = select(VenditeImax).where(VenditeImax.ordine == ordine_name)
            exists = db.exec(statement).first()
            if exists:
                continue  
            
            
            # Product
            product_raw = line['product_template_id'][1] if line.get('product_template_id') else 'N/A'
            match = re.match(r'\[(.*?)\]\s*(.*)', product_raw)
            if match:
                code_product, desc_product = match.groups()
                print(f"  Product: {code_product} | {desc_product}")
            else:
                code_product, desc_product = "N/A", product_raw
                #print(f"  Product: {product_raw}")
                
            # Description
            desc_raw = line['name']
            match = re.match(r'\[(.*?)\]\s*(.*)', desc_raw)
            if match:
                code, desc = match.groups()
                print(f"  Description: {code} | {desc}")
            else:
                code, desc = "N/A", desc_raw
                #print(f"  Description: {desc_raw}")
            try:
                vendite = VenditeImax(
                    ordine=order.get("name", "N/A"),
                    data=order.get("date_order"),
                    venditore=order["user_id"][1] if order.get("user_id") else "N/A",
                    team=order["team_id"][1] if order.get("team_id") else "N/A",
                    cliente=order["partner_id"][1] if order.get("partner_id") else "N/A",
                    prodotto=f"{code_product} | {desc_product}",
                    descrizione=f"{code} | {desc}",
                    quantita=line.get("product_uom_qty", 0),
                    prezzo_unitario=line.get("price_unit", 0),
                    costo_unitario=line.get("cost_line_related", 0),
                    ricarico=line.get("recharge", 0),
                    subtotale=line.get("price_subtotal", 0)
                )
                db.add(vendite)
                inserted += 1
                
            except Exception as inner_e:
                print(f"Skipping order {order.get('name')} due to error: {inner_e}")
                
            db.commit()
        return JSONResponse(content={"message": "Sync complete", "inserted": inserted}, status_code=200)

    except Exception as e:
        print(f"Error fetching sale order lines: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
