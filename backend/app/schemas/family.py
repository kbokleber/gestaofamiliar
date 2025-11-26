from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FamilyBase(BaseModel):
    name: str
    codigo_unico: str

class FamilyCreate(FamilyBase):
    pass

class FamilyUpdate(BaseModel):
    name: Optional[str] = None
    codigo_unico: Optional[str] = None

class Family(FamilyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

