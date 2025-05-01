import sys
import os

if os.getenv("GITHUB_ACTIONS"):sys.path.append(os.path.dirname(__file__)) 
from sqlmodel import Session, select
from models.items import Item

def create_item(session: Session, item_data):
    item = Item(**item_data.dict())  # Convert Pydantic model to DB model
    session.add(item)
    session.commit()
    session.refresh(item)  # Refresh to get auto-generated fields like id
    return item

def get_items(session: Session):
    return session.exec(select(Item)).all()
