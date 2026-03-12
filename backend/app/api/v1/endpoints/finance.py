from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
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
from app.utils.ai_vision import analyze_receipt

router = APIRouter()

# ----- CATEGORIES -----

@router.get("/categories", response_model=List[CategorySchema])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Lista as categorias da família"""
    from app.api.deps import get_user_family_ids
    
    query = db.query(FinanceCategory).filter(FinanceCategory.is_active == True)
    
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        query = query.filter(FinanceCategory.family_id.in_(family_ids))
    elif family_id:
        query = query.filter(FinanceCategory.family_id == family_id)
    else:
        return []

    return query.order_by(FinanceCategory.name).all()

@router.post("/categories", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: FinanceCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Cria uma nova categoria"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")

    try:
        dump = category_data.model_dump()
        now = datetime.now()
        category = FinanceCategory(
            **dump,
            family_id=family_id,
            created_by_id=current_user.id,
            created_at=now
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Erro ao criar categoria: {str(e)} - Dump: {dump} - Family: {family_id}")
        raise

@router.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    category_data: FinanceCategoryUpdate,
    db: Session = Depends(get_db),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualiza uma categoria"""
    category = db.query(FinanceCategory).filter(
        FinanceCategory.id == category_id
    )
    
    # Se não for superuser, filtrar pela família
    if family_id:
        category = category.filter(FinanceCategory.family_id == family_id)
        
    category = category.first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Exclui uma categoria"""
    query = db.query(FinanceCategory).filter(FinanceCategory.id == category_id)
    
    if family_id:
        query = query.filter(FinanceCategory.family_id == family_id)
        
    category = query.first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    db.delete(category)
    db.commit()
    return None

# ----- ENTRIES -----

@router.get("/entries", response_model=List[EntrySchema])
async def list_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Lista os lançamentos com filtros"""
    from app.api.deps import get_user_family_ids
    
    query = db.query(FinanceEntry).options(joinedload(FinanceEntry.category))
    
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        query = query.filter(FinanceEntry.family_id.in_(family_ids))
    elif family_id:
        query = query.filter(FinanceEntry.family_id == family_id)
    else:
        return []
    
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
    family_id: Optional[int] = Depends(get_current_family)
):
    """Cria um novo lançamento"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")

    try:
        dump = entry_data.model_dump()
        now = datetime.now()
        entry = FinanceEntry(
            **dump,
            family_id=family_id,
            created_by_id=current_user.id,
            created_at=now,
            updated_at=now
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Erro ao criar lançamento: {str(e)} - Dump: {dump} - Family: {family_id} - User: {current_user.id}")
        raise

@router.put("/entries/{entry_id}", response_model=EntrySchema)
async def update_entry(
    entry_id: int,
    entry_data: FinanceEntryUpdate,
    db: Session = Depends(get_db),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualiza um lançamento"""
    query = db.query(FinanceEntry).filter(FinanceEntry.id == entry_id)
    
    if family_id:
        query = query.filter(FinanceEntry.family_id == family_id)
        
    entry = query.first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    update_data = entry_data.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now()
    for key, value in update_data.items():
        setattr(entry, key, value)
        
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Exclui um lançamento"""
    query = db.query(FinanceEntry).filter(FinanceEntry.id == entry_id)
    
    if family_id:
        query = query.filter(FinanceEntry.family_id == family_id)
        
    entry = query.first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    db.delete(entry)
    db.commit()
    return None

@router.post("/upload-receipt", response_model=EntrySchema)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """
    Recebe um comprovante (imagem), usa IA para extrair dados 
    e cadastra a despesa automaticamente.
    """
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]
    elif family_id is None:
        raise HTTPException(status_code=400, detail="Família não identificada.")
        
    # Ler conteúdo do arquivo
    contents = await file.read()
    
    # Chamar IA para analisar
    ai_data = analyze_receipt(contents, family_id, db)
    
    if not ai_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível extrair dados deste comprovante. Verifique a configuração de IA da família ou a qualidade da imagem."
        )
    
    # 1. Resolver Categoria
    cat_name = ai_data.get("category_name", "Geral")
    category = db.query(FinanceCategory).filter(
        FinanceCategory.family_id == family_id,
        func.lower(FinanceCategory.name) == cat_name.lower()
    ).first()
    
    if not category:
        # Criar categoria automaticamente se não existir
        category = FinanceCategory(
            name=cat_name,
            type='EXPENSE',
            family_id=family_id,
            color='#6366f1' # Indigo default
        )
        db.add(category)
        db.flush()
        
    # 2. Criar Lançamento
    try:
        amount_raw = ai_data.get("amount", 0)
        # Limpar string de valor se necessário
        if isinstance(amount_raw, str):
            amount_raw = amount_raw.replace('R$', '').replace('$', '').replace(',', '.').strip()
        amount = Decimal(str(amount_raw))
        
        date_raw = ai_data.get("date")
        if date_raw:
            entry_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
        else:
            entry_date = date.today()
    except Exception:
        amount = Decimal('0.00')
        entry_date = date.today()
        
    entry = FinanceEntry(
        description=ai_data.get("description", "Lançamento via IA"),
        amount=amount,
        date=entry_date,
        type='EXPENSE',
        category_id=category.id,
        family_id=family_id,
        created_by_id=current_user.id,
        is_paid=True # Geralmente comprovante já está pago
    )
    
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return entry

# ----- RECURRENCES -----

@router.get("/recurrences", response_model=List[RecurrenceSchema])
async def list_recurrences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Lista as recorrências ativas"""
    from app.api.deps import get_user_family_ids
    
    query = db.query(FinanceRecurrence).options(joinedload(FinanceRecurrence.category))
    
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        query = query.filter(FinanceRecurrence.family_id.in_(family_ids))
    elif family_id:
        query = query.filter(FinanceRecurrence.family_id == family_id)
    else:
        return []
        
    return query.all()

@router.post("/recurrences", response_model=RecurrenceSchema, status_code=status.HTTP_201_CREATED)
async def create_recurrence(
    recurrence_data: FinanceRecurrenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Cria uma nova configuração de recorrência"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")

    recurrence = FinanceRecurrence(
        **recurrence_data.model_dump(),
        family_id=family_id,
        created_by_id=current_user.id,
        created_at=datetime.now()
    )
    db.add(recurrence)
    db.commit()
    db.refresh(recurrence)
    return recurrence

@router.put("/recurrences/{recurrence_id}", response_model=RecurrenceSchema)
async def update_recurrence(
    recurrence_id: int,
    recurrence_data: FinanceRecurrenceUpdate,
    db: Session = Depends(get_db),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualiza uma recorrência"""
    query = db.query(FinanceRecurrence).filter(FinanceRecurrence.id == recurrence_id)
    
    if family_id:
        query = query.filter(FinanceRecurrence.family_id == family_id)
        
    recurrence = query.first()
    
    if not recurrence:
        raise HTTPException(status_code=404, detail="Recorrência não encontrada")
    
    update_data = recurrence_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(recurrence, key, value)
        
    db.commit()
    db.refresh(recurrence)
    return recurrence

@router.delete("/recurrences/{recurrence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurrence(
    recurrence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Exclui uma recorrência"""
    query = db.query(FinanceRecurrence).filter(FinanceRecurrence.id == recurrence_id)
    
    if family_id:
        query = query.filter(FinanceRecurrence.family_id == family_id)
        
    recurrence = query.first()
    
    if not recurrence:
        raise HTTPException(status_code=404, detail="Recorrência não encontrada")
    
    db.delete(recurrence)
    db.commit()
    return None

# ----- DASHBOARD & SUMMARY -----

@router.get("/summary", response_model=FinanceSummary)
async def get_finance_summary(
    month: Optional[int] = Query(None),
    year: int = Query(default=datetime.now().year),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Obtém o resumo financeiro do mês"""
    from app.api.deps import get_user_family_ids
    
    # Resolver family_ids para o filtro
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        f_ids = get_user_family_ids(current_user, db)
    elif family_id:
        f_ids = [family_id]
    else:
        f_ids = []

    # Opcional: Gerar recorrências automaticamente para o mês visualizado
    now_dt = datetime.now()
    if f_ids:
        # Tentar gerar para cada família encontrada (simplificado)
        for fid in f_ids:
            try:
                # Reutilizando a lógica de geração interna (pode ser refatorado depois)
                query_rec = db.query(FinanceRecurrence).filter(
                    FinanceRecurrence.family_id == fid,
                    FinanceRecurrence.is_active == True
                )
                recurrences = query_rec.all()
                month_start = date(year, month, 1)
                
                for rec in recurrences:
                    # Verificar se o mês visualizado está dentro da vigência da recorrência
                    month_start = date(year, month, 1)
                    # Último dia do mês visualizado
                    if month == 12:
                        next_month_start = date(year + 1, 1, 1)
                    else:
                        next_month_start = date(year, month + 1, 1)
                    month_end = next_month_start - timedelta(days=1)

                    # Se a recorrência começa depois do fim do mês visualizado, pular
                    if rec.start_date and rec.start_date > month_end:
                        continue
                    # Se a recorrência termina antes do início do mês visualizado, pular
                    if rec.end_date and rec.end_date < month_start:
                        continue
                    
                    # Verificar se já existe um lançamento para esta recorrência neste mês/ano
                    existing_entry = db.query(FinanceEntry).filter(
                        FinanceEntry.recurrence_id == rec.id,
                        extract('month', FinanceEntry.date) == month,
                        extract('year', FinanceEntry.date) == year
                    ).first()

                    if not existing_entry:
                        # Determinar o dia do lançamento (não pode passar do fim do mês)
                        day = min(rec.day_of_month, month_end.day)
                        entry_date = date(year, month, day)
                        
                        entry = FinanceEntry(
                            family_id=fid,
                            category_id=rec.category_id,
                            description=f"[RECORRENTE] {rec.description}",
                            amount=rec.amount,
                            date=entry_date,
                            type=rec.type,
                            is_paid=False,
                            recurrence_id=rec.id,
                            created_by_id=current_user.id,
                            created_at=now_dt,
                            updated_at=now_dt
                        )
                        db.add(entry)
                        # Atualizar a data de última geração para fins de auditoria/histórico
                        rec.last_generated_date = now_dt.date()
                db.commit()
            except Exception as e:
                db.rollback()
                import logging
                logging.error(f"Erro na auto-geração de recorrências: {e}")

    # Receitas do período (mês ou ano todo)
    income_query = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id.in_(f_ids),
        FinanceEntry.type == 'INCOME',
        extract('year', FinanceEntry.date) == year
    )
    if month:
        income_query = income_query.filter(extract('month', FinanceEntry.date) == month)
    income = income_query.scalar() or Decimal('0.00')
    
    # Despesas do período
    expense_query = db.query(func.sum(FinanceEntry.amount)).filter(
        FinanceEntry.family_id.in_(f_ids),
        FinanceEntry.type == 'EXPENSE',
        extract('year', FinanceEntry.date) == year
    )
    if month:
        expense_query = expense_query.filter(extract('month', FinanceEntry.date) == month)
    expense = expense_query.scalar() or Decimal('0.00')
    
    # Saldo acumulado (período anterior)
    if month:
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        prev_income = db.query(func.sum(FinanceEntry.amount)).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'INCOME',
            extract('month', FinanceEntry.date) == prev_month,
            extract('year', FinanceEntry.date) == prev_year
        ).scalar() or Decimal('0.00')
        
        prev_expense = db.query(func.sum(FinanceEntry.amount)).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'EXPENSE',
            extract('month', FinanceEntry.date) == prev_month,
            extract('year', FinanceEntry.date) == prev_year
        ).scalar() or Decimal('0.00')
    else:
        # Se for o ano todo, comparar com o ano anterior
        prev_year = year - 1
        prev_income = db.query(func.sum(FinanceEntry.amount)).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'INCOME',
            extract('year', FinanceEntry.date) == prev_year
        ).scalar() or Decimal('0.00')
        prev_expense = db.query(func.sum(FinanceEntry.amount)).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'EXPENSE',
            extract('year', FinanceEntry.date) == prev_year
        ).scalar() or Decimal('0.00')
    
    # Estatísticas por categoria (Despesas)
    cat_query = db.query(
        FinanceCategory.name,
        func.sum(FinanceEntry.amount).label('total'),
        FinanceCategory.color
    ).join(FinanceEntry, FinanceEntry.category_id == FinanceCategory.id).filter(
        FinanceEntry.family_id.in_(f_ids),
        FinanceEntry.type == 'EXPENSE',
        extract('year', FinanceEntry.date) == year
    )
    if month:
        cat_query = cat_query.filter(extract('month', FinanceEntry.date) == month)
    
    cat_stats = cat_query.group_by(FinanceCategory.name, FinanceCategory.color).all()

    # Dados mensais para gráfico de evolução (ano todo)
    monthly_data = None
    if not month:
        m_income = db.query(
            extract('month', FinanceEntry.date).label('month'),
            func.sum(FinanceEntry.amount).label('total')
        ).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'INCOME',
            extract('year', FinanceEntry.date) == year
        ).group_by(extract('month', FinanceEntry.date)).all()

        m_expense = db.query(
            extract('month', FinanceEntry.date).label('month'),
            func.sum(FinanceEntry.amount).label('total')
        ).filter(
            FinanceEntry.family_id.in_(f_ids),
            FinanceEntry.type == 'EXPENSE',
            extract('year', FinanceEntry.date) == year
        ).group_by(extract('month', FinanceEntry.date)).all()

        # Mesclar resultados mensais (1-12)
        m_dict = {i: {"month": i, "income": Decimal('0.00'), "expense": Decimal('0.00')} for i in range(1, 13)}
        for m, total in m_income:
            m_dict[int(m)]["income"] = total
        for m, total in m_expense:
            m_dict[int(m)]["expense"] = total
        
        monthly_data = list(m_dict.values())

    return {
        "month_income": income,
        "month_expense": expense,
        "month_balance": income - expense,
        "previous_month_balance": prev_income - prev_expense,
        "expenses_by_category": [{"category_name": name, "amount": total, "color": color} for name, total, color in cat_stats],
        "monthly_data": monthly_data
    }

# ----- BULK GENERATE FROM RECURRENCES -----

@router.post("/generate-recurrences")
async def generate_monthly_recurrences(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Gera lançamentos para um mês específico baseados nas recorrências ativas"""
    today = date.today()
    if not month: month = today.month
    if not year: year = today.year
    current_month_start = today.replace(day=1)
    
    query = db.query(FinanceRecurrence).filter(
        FinanceRecurrence.is_active == True
    )
    
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        from app.api.deps import get_user_family_ids
        family_ids = get_user_family_ids(current_user, db)
        query = query.filter(FinanceRecurrence.family_id.in_(family_ids))
    elif family_id:
        query = query.filter(FinanceRecurrence.family_id == family_id)
    else:
        return {"message": "Nenhuma família especificada."}
        
    recurrences = query.all()
    
    # Se não informar o mês, processar o ano todo
    months_to_process = [month] if month else list(range(1, 13))
    generated_count = 0

    for m in months_to_process:
        for rec in recurrences:
            # Usar o mês/ano solicitado
            month_start = date(year, m, 1)
            if m == 12:
                next_month_start = date(year + 1, 1, 1)
            else:
                next_month_start = date(year, m + 1, 1)
            month_end = next_month_start - timedelta(days=1)

            # Verificar vigência
            if rec.start_date and rec.start_date > month_end:
                continue
            if rec.end_date and rec.end_date < month_start:
                continue
                
            # Verificar duplicatas
            existing = db.query(FinanceEntry).filter(
                FinanceEntry.recurrence_id == rec.id,
                extract('month', FinanceEntry.date) == m,
                extract('year', FinanceEntry.date) == year
            ).first()

            if existing:
                continue
                
            # Criar lançamento
            day = min(rec.day_of_month, month_end.day)
            entry_date = date(year, m, day)
            
            entry = FinanceEntry(
                family_id=rec.family_id,
                category_id=rec.category_id,
                description=f"[RECORRENTE] {rec.description}",
                amount=rec.amount,
                date=entry_date,
                type=rec.type,
                is_paid=False,
                recurrence_id=rec.id,
                created_by_id=current_user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(entry)
            rec.last_generated_date = today
            generated_count += 1
        
    db.commit()
    return {"message": f"Gerados {generated_count} lançamentos recorrentes."}
