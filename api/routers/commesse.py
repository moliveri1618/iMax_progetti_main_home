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
from models.commesse import iCommesse
from schemas.commesse import ICommesseCreate, ICommesseRead, ICommesseUpdate
from dependecies import get_db, SERVER_URL_ODOO, DB_NAME_ODOO, USERNAME_ODOO, PASSWORD_ODOO

router = APIRouter()

# 
# Get all
@router.get("/all", response_model=List[ICommesseRead])
def read_commesse(db: Session = Depends(get_db)):
    commesse = db.exec(select(iCommesse)).all()
    return commesse


@router.get("/odoo")
def get_commesse_from_odoo(db: Session = Depends(get_db)):
    
    #test
    return JSONResponse(content={"message": "Sync complete", "inserted": 1}, status_code=200)

        
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

        if not sale_order_ids:
            return JSONResponse(content={"message": "No sales orders found."}, status_code=404)


        # Step 2: Read sale order data
        sale_orders = models.execute_kw(
            DB_NAME_ODOO, user_id, PASSWORD_ODOO,
            'sale.order', 'read',
            [sale_order_ids],
            {'fields': [
                'name',            # Numero
                'date_order',      # Data ordine
                'partner_id',      # Cliente
                'user_id',         # Addetto vendite
                'activity_ids',    # Attività (IDs)
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
                inserted += 1

            except Exception as inner_e:
                print(f"Skipping order {order.get('name')} due to error: {inner_e}")
                
            db.commit()
            
            # order_dict = {
            #     "order": order['name'],
            #     "date": order['date_order'],
            #     "customer": order['partner_id'][1] if order['partner_id'] else "N/A",
            #     "salesperson": order['user_id'][1] if order['user_id'] else "N/A",
            #     "total": f"{order['amount_total']} €",
            #     "invoice_status": order['invoice_status'],
            #     "cost": f"{order.get('total_cost_of_lines', 'N/A')} €",
            #     "recharge": f"{order.get('total_recharge', 'N/A')} €",
            #     "products": []
            # }
            # print(f"\nOrder: {order['name']}")
            # print(f"  Date: {order['date_order']}")
            # print(f"  Customer: {order['partner_id'][1] if order['partner_id'] else 'N/A'}")
            # print(f"  Salesperson: {order['user_id'][1] if order['user_id'] else 'N/A'}")
            # print(f"  Total: {order['amount_total']} €")
            # print(f"  Invoice Status: {order['invoice_status']}")
            # print(f"  Cost: {order.get('total_cost_of_lines', 'N/A')} €")
            # print(f"  Recharge: {order.get('total_recharge', 'N/A')} €")

            # # Show related products
            # products = order_to_products.get(order['id'], [])
            # # print("  Products:")
            # for prod in products:
            #     match = re.match(r'\[(.*?)\]\s*(.*)', prod)
            #     if match:
            #         code, desc = match.groups()
            #         order_dict["products"].append(f"{code} | {desc}")
            #         # print(f"    - {code} | {desc}")
            #     else:
            #         order_dict["products"].append(prod)
            #         # print(f"    - {prod}")
                    
            # final_output.append(order_dict)
        return JSONResponse(content={"message": "Sync complete", "inserted": inserted}, status_code=200)

    except Exception as e:
        print(f"Error fetching sales orders: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)




# # Delete
# @router.delete("/{commessa_id}", status_code=204)
# def delete_commessa(commessa_id: int, db: Session = Depends(get_db)):
#     commessa = db.get(iCommesse, commessa_id)
#     if not commessa:
#         raise HTTPException(status_code=404, detail="Commessa not found")
#     db.delete(commessa)
#     db.commit()


# # Get one
# @router.get("/{commessa_id}", response_model=ICommesseRead)
# def read_commessa(commessa_id: int, db: Session = Depends(get_db)):
#     commessa = db.get(iCommesse, commessa_id)
#     if not commessa:
#         raise HTTPException(status_code=404, detail="Commessa not found")
#     return commessa

# # Update
# @router.put("/{commessa_id}", response_model=ICommesseRead)
# def update_commessa(commessa_id: int, commessa_update: ICommesseUpdate, db: Session = Depends(get_db)):
#     commessa = db.get(iCommesse, commessa_id)
#     if not commessa:
#         raise HTTPException(status_code=404, detail="Commessa not found")
#     update_data = commessa_update.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(commessa, key, value)
#     db.add(commessa)
#     db.commit()
#     db.refresh(commessa)
#     return commessa


# Create
# @router.post("", response_model=ICommesseRead)
# def create_commessa(commessa: ICommesseCreate, db: Session = Depends(get_db)):
#     db_commessa = iCommesse(**commessa.model_dump())
#     db.add(db_commessa)
#     db.commit()
#     db.refresh(db_commessa)
#     return db_commessa
