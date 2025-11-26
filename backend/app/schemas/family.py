from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FamilyBase(BaseModel):
    name: str

class FamilyCreate(FamilyBase):
    """Schema para criar família - código único é gerado automaticamente"""
    pass

class FamilyUpdate(BaseModel):
    """Schema para atualizar família - código único não pode ser alterado"""
    name: Optional[str] = None

class Family(FamilyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

