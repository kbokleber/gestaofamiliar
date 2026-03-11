from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.db.base import get_db
from app.models.user import User
from app.models.finance import FinanceCategory, FinanceEntry, FinanceRecurrence
from app.schemas.finance import (
    FinanceCategory as CategorySchema, FinanceCategoryCreate, FinanceCategoryUpdate,
    FinanceEntry as EntrySchema, FinanceEntryCreate, FinanceEntryUpdate,
    FinanceRecurrence as RecurrenceSchema, FinanceRecurrenceCreate, FinanceRecurrenceUpdate,
    FinanceSummary
)
from app.api.deps import get_current_user, get_current_family

router = APIRouter()

# ----- CATEGORIES -----

@router.get("/categories", response_model=List[CategorySchema])
async def list_categories(
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Lista as categorias da família"""
    return db.query(FinanceCategory).filter(
        FinanceCategory.family_id == family_id,
        FinanceCategory.is_active == True
    ).order_by(FinanceCategory.name).all()

@router.post("/categories", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: FinanceCategoryCreate,
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Cria uma nova categoria"""
    category = FinanceCategory(**category_data.model_dump(), family_id=family_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    category_data: FinanceCategoryUpdate,
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Atualiza uma categoria"""
    category = db.query(FinanceCategory).filter(
        FinanceCategory.id == category_id,
        FinanceCategory.family_id == family_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category

# ----- ENTRIES -----

@router.get("/entries", response_model=List[EntrySchema])
async def list_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Lista os lançamentos com filtros"""
    query = db.query(FinanceEntry).options(joinedload(FinanceEntry.category)).filter(
        FinanceEntry.family_id == family_id
    )
    
    if start_date:
        query = query.filter(FinanceEntry.date >= start_date)
    if end_date:
        query = query.filter(FinanceEntry.date <= end_date)
    if category_id:
        query = query.filter(FinanceEntry.category_id == category_id)
    if type:
        query = query.filter(FinanceEntry.type == type)
        
    return query.order_by(FinanceEntry.date.desc(), FinanceEntry.created_at.desc()).all()

@router.post("/entries", response_model=EntrySchema, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: FinanceEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Cria um novo lançamento"""
    entry = FinanceEntry(
        **entry_data.model_dump(),
        family_id=family_id,
        created_by_id=current_user.id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@router.put("/entries/{entry_id}", response_model=EntrySchema)
async def update_entry(
    entry_id: int,
    entry_data: FinanceEntryUpdate,
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Atualiza um lançamento"""
    entry = db.query(FinanceEntry).filter(
        FinanceEntry.id == entry_id,
        FinanceEntry.family_id == family_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    update_data = entry_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)
        
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Exclui um lançamento"""
    entry = db.query(FinanceEntry).filter(
        FinanceEntry.id == entry_id,
        FinanceEntry.family_id == family_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    db.delete(entry)
    db.commit()
    return None

# ----- RECURRENCES -----

@router.get("/recurrences", response_model=List[RecurrenceSchema])
async def list_recurrences(
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Lista as recorrências ativas"""
    return db.query(FinanceRecurrence).options(joinedload(FinanceRecurrence.category)).filter(
        FinanceRecurrence.family_id == family_id
    ).all()

@router.post("/recurrences", response_model=RecurrenceSchema, status_code=status.HTTP_201_CREATED)
async def create_recurrence(
    recurrence_data: FinanceRecurrenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Cria uma nova configuração de recorrência"""
    recurrence = FinanceRecurrence(
        **recurrence_data.model_dump(),
        family_id=family_id,
        created_by_id=current_user.id
    )
    db.add(recurrence)
    db.commit()
    db.refresh(recurrence)
    return recurrence

# ----- DASHBOARD & SUMMARY -----

@router.get("/summary", response_model=FinanceSummary)
async def get_finance_summary(
    month: int = Query(default=datetime.now().month),
    year: int = Query(default=datetime.now().year),
    db: Session = Depends(get_db),
    family_id: int = Depends(get_current_family)
):
    """Obtém o resumo financeiro do mês"""
    # Receitas do mês
    income = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id == family_id,
        FinanceEntry.type == 'INCOME',
        extract('month', FinanceEntry.date) == month,
        extract('year', FinanceEntry.date) == year,
        FinanceEntry.is_paid == True
    ).scalar() or Decimal('0.00')
    
    # Despesas do mês
    expense = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id == family_id,
        FinanceEntry.type == 'EXPENSE',
        extract('month', FinanceEntry.date) == month,
        extract('year', FinanceEntry.date) == year,
        FinanceEntry.is_paid == True
    ).scalar() or Decimal('0.00')
    
    # Saldo acumulado (simplificado: total histórico de entradas - total histórico de saídas)
    # Na verdade, o usuário pediu "previous_month_balance", vamos fazer do mês anterior
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    prev_income = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id == family_id,
        FinanceEntry.type == 'INCOME',
        extract('month', FinanceEntry.date) == prev_month,
        extract('year', FinanceEntry.date) == prev_year,
        FinanceEntry.is_paid == True
    ).scalar() or Decimal('0.00')
    
    prev_expense = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id == family_id,
        FinanceEntry.type == 'EXPENSE',
        extract('month', FinanceEntry.date) == prev_month,
        extract('year', FinanceEntry.date) == prev_year,
        FinanceEntry.is_paid == True
    ).scalar() or Decimal('0.00')
    
    # Estatísticas por categoria (Despesas)
    cat_stats = db.query(
        FinanceCategory.name,
        func.sum(FinanceEntry.amount).label('total'),
        FinanceCategory.color
    ).join(FinanceEntry, FinanceEntry.category_id == FinanceCategory.id).filter(
        FinanceEntry.family_id == family_id,
        FinanceEntry.type == 'EXPENSE',
        extract('month', FinanceEntry.date) == month,
        extract('year', FinanceEntry.date) == year,
        FinanceEntry.is_paid == True
    ).group_by(FinanceCategory.name, FinanceCategory.color).all()
    
    return {
        "month_income": income,
        "month_expense": expense,
        "month_balance": income - expense,
        "previous_month_balance": prev_income - prev_expense,
        "expenses_by_category": [{"category_name": name, "amount": total, "color": color} for name, total, color in cat_stats]
    }

# ----- BULK GENERATE FROM RECURRENCES -----

@router.post("/generate-recurrences")
async def generate_monthly_recurrences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Gera lançamentos para o mês atual baseados nas recorrências ativas"""
    today = date.today()
    current_month_start = today.replace(day=1)
    
    recurrences = db.query(FinanceRecurrence).filter(
        FinanceRecurrence.family_id == family_id,
        FinanceRecurrence.is_active == True
    ).all()
    
    generated_count = 0
    for rec in recurrences:
        # Verificar se já gerou este mês
        if rec.last_generated_date and rec.last_generated_date >= current_month_start:
            continue
            
        # Criar lançamento
        entry_date = today.replace(day=min(rec.day_of_month, 28)) # Simplificado para evitar erros em meses curtos
        entry = FinanceEntry(
            family_id=family_id,
            category_id=rec.category_id,
            description=f"[RECORRENTE] {rec.description}",
            amount=rec.amount,
            date=entry_date,
            type=rec.type,
            is_paid=False, # Geralmente começa como não pago
            recurrence_id=rec.id,
            created_by_id=current_user.id
        )
        db.add(entry)
        rec.last_generated_date = today
        generated_count += 1
        
    db.commit()
    return {"message": f"Gerados {generated_count} lançamentos recorrentes."}
