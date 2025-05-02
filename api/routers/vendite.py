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


# @router.get("/odoo/vendite")
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
        #print("\n📦 Sale Order Lines with Related Fields:")
        seen_orders = set()
        count = 0
        for line in sale_order_lines:
            order = order_data.get(line['order_id'][0]) if line.get('order_id') else {}
            
            # Skip duplicate orders
            ordine_name = order.get("name", "N/A")
            if ordine_name in seen_orders:
                continue  
            seen_orders.add(ordine_name)

            # print(f"\nOrder: {order.get('name', 'N/A')}")
            # print(f"  Salesperson: {order['user_id'][1] if order.get('user_id') else 'N/A'}")
            # print(f"  Team: {order['team_id'][1] if order.get('team_id') else 'N/A'}")
            # print(f"  Customer: {order['partner_id'][1] if order.get('partner_id') else 'N/A'}")
            # print(f"  Date: {order.get('date_order', 'N/A')}")
            
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

            # Save to DB
            db.add(vendite)
            count+=1

                
            # print(f"  Qty: {line['product_uom_qty']}")
            # print(f"  Unit Price: {line['price_unit']} €")
            # print(f"  Cost: {line.get('cost_line_related', 0)} €")
            # print(f"  Recharge: {line.get('recharge', 0)} €")
            # print(f"  Subtotal: {line['price_subtotal']} €")
        db.commit()


    except Exception as e:
        print(f"Error fetching sale order lines: {e}")
    
    return {"records_added": count}


# @router.delete("/odoo/vendite/cleanup-duplicates")
def delete_latest_duplicates(db: Session = Depends(get_db)):
    try:
        # Step 1: Fetch all vendite
        all_entries = db.exec(select(VenditeImax)).all()

        # Step 2: Group by 'ordine'
        grouped = defaultdict(list)
        for entry in all_entries:
            grouped[entry.ordine].append(entry)

        deleted = 0

        # Step 3: For each group with more than one entry
        for ordine, entries in grouped.items():
            if len(entries) > 1:
                try:
                    sorted_entries = sorted(
                        entries,
                        key=lambda e: datetime.fromisoformat(e.data),
                        reverse=True
                    )
                except Exception as e:
                    print(f"Error parsing date for ordine {ordine}: {e}")
                    continue

                db.delete(sorted_entries[0])
                deleted += 1


        db.commit()
        return {"records_deleted": deleted}

    except Exception as e:
        print(f"❌ Error cleaning duplicates: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la pulizia dei duplicati")
    
from time import sleep
@router.delete("/porcodiooooooo")
def yoyoyoooo(db: Session = Depends(get_db)):
    result1 = get_vendite_from_odoo(db)  # Waits until this is done
    sleep(5)  # Optional wait
    result2 = delete_latest_duplicates(db)
    return {
        "vendite_result": result1,
        "cleanup_result": result2
    }
