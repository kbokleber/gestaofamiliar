from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal
import datetime
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
    family_id: Optional[int] = None
    is_active: Optional[bool] = None
    id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(extra='allow')

class FinanceCategory(FinanceCategoryBase):
    id: int
    family_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# ----- ENTRIES -----
class FinanceEntryBase(BaseModel):
    description: str
    amount: Decimal
    date: datetime.date
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
    date: Optional[datetime.date] = None
    type: Optional[str] = None
    category_id: Optional[int] = None
    payment_method: Optional[str] = None
    is_paid: Optional[bool] = None
    notes: Optional[str] = None
    documents: Optional[str] = None
    family_id: Optional[int] = None
    recurrence_id: Optional[int] = None
    category: Optional[dict] = None
    id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    created_by_id: Optional[int] = None
    recurrence: Optional[dict] = None

    model_config = ConfigDict(extra='allow')

class FinanceEntry(FinanceEntryBase):
    id: int
    family_id: int
    recurrence_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    category: Optional[FinanceCategory] = None

    class Config:
        from_attributes = True


# ----- BANK IMPORT / BULK -----
class SuggestImportCategoryItem(BaseModel):
    description: str
    type: str  # INCOME ou EXPENSE


class SuggestImportCategoriesRequest(BaseModel):
    items: List[SuggestImportCategoryItem] = Field(..., max_length=500)


class SuggestImportCategoryResult(BaseModel):
    category_id: Optional[int] = None
    confidence: Optional[Literal["high", "low"]] = None


class SuggestImportCategoriesResponse(BaseModel):
    suggestions: List[SuggestImportCategoryResult]


class FinanceEntryBulkCreate(BaseModel):
    entries: List[FinanceEntryCreate] = Field(..., max_length=500)


class FinanceEntryBulkError(BaseModel):
    index: int
    detail: str


class FinanceEntryBulkResult(BaseModel):
    created: int
    errors: List[FinanceEntryBulkError] = Field(default_factory=list)


class FinanceEntryBulkIds(BaseModel):
    entry_ids: List[int] = Field(..., min_length=1, max_length=500)


class FinanceEntryBulkCategoryBody(BaseModel):
    entry_ids: List[int] = Field(..., min_length=1, max_length=500)
    category_id: Optional[int] = None


class FinanceEntryBulkDeleteResult(BaseModel):
    deleted: int


class FinanceEntryBulkCategoryResult(BaseModel):
    updated: int
    skipped: int = 0


# ----- IMPORT CATEGORY RULES -----
ImportRuleEntryType = Literal["EXPENSE", "INCOME", "BOTH"]


class FinanceImportCategoryRuleBase(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)
    category_id: int
    entry_type: ImportRuleEntryType
    priority: int = 100
    is_active: bool = True


class FinanceImportCategoryRuleCreate(FinanceImportCategoryRuleBase):
    pass


class FinanceImportCategoryRuleUpdate(BaseModel):
    pattern: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    entry_type: Optional[ImportRuleEntryType] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class FinanceImportCategoryRule(FinanceImportCategoryRuleBase):
    id: int
    family_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    category: Optional[FinanceCategory] = None

    model_config = ConfigDict(from_attributes=True)


# ----- RECURRENCES -----
class FinanceRecurrenceBase(BaseModel):
    description: str
    amount: Decimal
    type: str # 'INCOME' ou 'EXPENSE'
    category_id: Optional[int] = None
    day_of_month: int # 1 a 31
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    is_active: bool = True

class FinanceRecurrenceCreate(FinanceRecurrenceBase):
    pass

class FinanceRecurrenceUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    type: Optional[str] = None
    category_id: Optional[int] = None
    day_of_month: Optional[int] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra='allow')

class FinanceRecurrence(FinanceRecurrenceBase):
    id: int
    family_id: int
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    last_generated_date: Optional[datetime.date] = None
    created_by_id: Optional[int] = None
    created_at: datetime.datetime
    category: Optional[FinanceCategory] = None

    class Config:
        from_attributes = True

# ----- SUMMARY / DASHBOARD -----
class FinanceSummary(BaseModel):
    month_income: Decimal
    month_expense: Decimal
    month_balance: Decimal
    previous_month_balance: Decimal
    expenses_by_category: List[dict]  # category_id, category_name, amount, color
    incomes_by_category: List[dict]  # category_id, category_name, amount, color
    monthly_data: Optional[List[dict]] = None # [{month: int, income: Decimal, expense: Decimal}]
