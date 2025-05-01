# schemas/items.py
from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    type: str
    owner: str

class ItemRead(ItemCreate):
    id: int
    
class ItemUpdate(BaseModel):
    type: Optional[str] = None
    owner: Optional[str] = None