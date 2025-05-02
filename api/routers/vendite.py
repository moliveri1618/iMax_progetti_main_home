from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import sys, os
from xmlrpc import client
from collections import defaultdict
import re
from fastapi.responses import JSONResponse
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from xmlrpc import client
from sqlalchemy import select
import re

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__))
from models.vendite import VenditeImax
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO


router = APIRouter()


@router.get("/odoo/vendite")
def get_vendite_from_odoo(db: Session = Depends(get_db)):
    try:
        # Connect to Odoo
        common = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/common')
        user_id = common.authenticate(DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO, {})
        if not user_id:
            raise Exception("Authentication failed")

        models = client.ServerProxy(f'{SERVER_URL_ODOO}/xmlrpc/2/object')

        # Fetch all sale order line fields
        sale_order_line_fields = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order.line', 'fields_get',
            [], {'attributes': ['string', 'type']}
        )
        all_line_fields = list(sale_order_line_fields.keys())

        # Fetch sale order lines
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
            {'fields': all_line_fields}
        )

        # Collect unique order IDs
        order_ids = list({line['order_id'][0] for line in sale_order_lines if line.get('order_id')})

        # Fetch all sale order fields
        sale_order_fields = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'fields_get',
            [], {'attributes': ['string', 'type']}
        )
        all_order_fields = list(sale_order_fields.keys())

        sale_orders = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'read',
            [order_ids],
            {'fields': all_order_fields}
        )
        order_data = {order['id']: order for order in sale_orders}

        # Insert into DB
        inserted = 0
        for line in sale_order_lines:
            try:
                order_id = line.get('order_id')[0] if line.get('order_id') else None
                order = order_data.get(order_id)

                if not order or not order.get('name'):
                    continue  # Skip lines without valid order

                ordine_name = order['name']

                # Skip duplicates
                exists = db.exec(select(VenditeImax).where(VenditeImax.ordine == ordine_name)).first()
                if exists:
                    continue

                # Product info
                product_raw = line['product_template_id'][1] if line.get('product_template_id') else 'N/A'
                match = re.match(r'\[(.*?)\]\s*(.*)', product_raw)
                code_product, desc_product = match.groups() if match else ("N/A", product_raw)

                # Description
                desc_raw = line.get('name', 'N/A')
                match = re.match(r'\[(.*?)\]\s*(.*)', desc_raw)
                code, desc = match.groups() if match else ("N/A", desc_raw)

                new_vendita = VenditeImax(
                    ordine=ordine_name,
                    data=order.get('date_order'),
                    venditore=order['user_id'][1] if order.get('user_id') else 'N/A',
                    team=order['team_id'][1] if order.get('team_id') else 'N/A',
                    cliente=order['partner_id'][1] if order.get('partner_id') else 'N/A',
                    prodotto=f"{code_product} | {desc_product}",
                    descrizione=f"{code} | {desc}",
                    quantita=line.get('product_uom_qty', 0),
                    prezzo_unitario=line.get('price_unit', 0),
                    costo_unitario=line.get('cost_line_related', 0),
                    ricarico=line.get('recharge', 0),
                    subtotale=line.get('price_subtotal', 0),
                )

                db.add(new_vendita)
                inserted += 1

            except Exception as inner_e:
                print(f"Skipping line due to error: {inner_e}")

        try:
            db.commit()
        except SQLAlchemyError as db_err:
            db.rollback()
            return JSONResponse(content={"error": f"Database commit failed: {str(db_err)}"}, status_code=500)

        return JSONResponse(content={"message": "Sync complete", "inserted": inserted}, status_code=200)

    except Exception as e:
        print(f"Error in get_vendite_from_odoo: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

