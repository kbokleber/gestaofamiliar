from pydantic import BaseModel, condecimal, field_validator
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

# ----- CATEGORIES -----
class FinanceCategoryBase(BaseModel):
    name: str
    icon: Optional[str] = "Wallet"
    color: Optional[str] = "#3b82f6"
    type: str # 'INCOME' ou 'EXPENSE'
    is_active: bool = True

class FinanceCategoryCreate(FinanceCategoryBase):
    pass

class FinanceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None

class FinanceCategory(FinanceCategoryBase):
    id: int
    family_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ----- ENTRIES -----
class FinanceEntryBase(BaseModel):
    description: str
    amount: Decimal
    date: date
    type: str # 'INCOME' ou 'EXPENSE'
    category_id: Optional[int] = None
    payment_method: Optional[str] = None
    is_paid: bool = True
    notes: Optional[str] = None
    documents: Optional[str] = None # JSON string

class FinanceEntryCreate(FinanceEntryBase):
    pass

class FinanceEntryUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[date] = None
    type: Optional[str] = None
    category_id: Optional[int] = None
    payment_method: Optional[str] = None
    is_paid: Optional[bool] = None
    notes: Optional[str] = None
    documents: Optional[str] = None

class FinanceEntry(FinanceEntryBase):
    id: int
    family_id: int
    recurrence_id: Optional[int] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[FinanceCategory] = None

    class Config:
        from_attributes = True

# ----- RECURRENCES -----
class FinanceRecurrenceBase(BaseModel):
    description: str
    amount: Decimal
    type: str # 'INCOME' ou 'EXPENSE'
    category_id: Optional[int] = None
    day_of_month: int # 1 a 31
    is_active: bool = True

class FinanceRecurrenceCreate(FinanceRecurrenceBase):
    pass

class FinanceRecurrenceUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    type: Optional[str] = None
    category_id: Optional[int] = None
    day_of_month: Optional[int] = None
    is_active: Optional[bool] = None

class FinanceRecurrence(FinanceRecurrenceBase):
    id: int
    family_id: int
    last_generated_date: Optional[date] = None
    created_by_id: int
    created_at: datetime
    category: Optional[FinanceCategory] = None

    class Config:
        from_attributes = True

# ----- SUMMARY / DASHBOARD -----
class FinanceSummary(BaseModel):
    month_income: Decimal
    month_expense: Decimal
    month_balance: Decimal
    previous_month_balance: Decimal
    expenses_by_category: List[dict] # {category_name: str, amount: Decimal, color: str}
