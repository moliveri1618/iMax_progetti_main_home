from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import SQLModel


# Base schema — used for Create & Update
class ICollaudoFinaleNauticaBase(BaseModel):
    workInProgress_id: Optional[int] = None
    rilievo_misure: Optional[float] = None
    collaudo_sarte: Optional[float] = None
    taglio_binario: Optional[float] = None
    image_paths_RM: Optional[List[str]] = []
    image_paths_CS: Optional[List[str]] = []
    image_paths_TB: Optional[List[str]] = []


# Create schema — used when creating a new record
class ICollaudoFinaleNauticaCreate(ICollaudoFinaleNauticaBase):
    pass


# Read schema — used in API responses
class ICollaudoFinaleNauticaRead(SQLModel):
    id: int
    workInProgress_id: Optional[int] = None
    rilievo_misure: Optional[float] = None
    collaudo_sarte: Optional[float] = None
    taglio_binario: Optional[float] = None
    image_paths_RM: Optional[List[str]] = []
    image_paths_CS: Optional[List[str]] = []
    image_paths_TB: Optional[List[str]] = []

    class Config:
        from_attributes = True


# Update schema — used for PATCH operations
class ICollaudoFinaleNauticaUpdate(BaseModel):
    workInProgress_id: Optional[int] = None
    rilievo_misure: Optional[float] = None
    collaudo_sarte: Optional[float] = None
    taglio_binario: Optional[float] = None
    image_paths_RM: Optional[List[str]] = None
    image_paths_CS: Optional[List[str]] = None
    image_paths_TB: Optional[List[str]] = None
