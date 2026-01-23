# 🕐 PROBLEMA DE TIMEZONE - SOLUÇÃO DEFINITIVA

## 📊 SITUAÇÃO ATUAL

### ✅ Banco de Dados: CORRETO
```sql
SELECT appointment_date FROM healthcare_medicalappointment WHERE id = 16;
-- Retorna: 2025-11-28 15:30:00.000 -0300
```

### ❌ Tela: ERRADO (mostra 18:30 ao invés de 15:30)
- Diferença de exatamente 3 horas
- Problema causado por conversão de timezone

---

## 🔍 CAUSA RAIZ

O problema ocorre em 3 etapas:

1. **PostgreSQL** armazena: `2025-11-28 15:30:00-03:00` ✅
2. **SQLAlchemy** lê como: `datetime(2025, 11, 28, 15, 30, tzinfo=-03:00)` ⚠️
3. **FastAPI/Pydantic** serializa como: `"2025-11-28T15:30:00-03:00"` ⚠️
4. **JavaScript** interpreta: "15:30 UTC-3" e converte para local (+3h = 18:30) ❌

---

## 💡 SOLUÇÃO DEFINITIVA

### Abordagem 1: Modificar Modelo SQLAlchemy (RECOMENDADO)

#### Passo 1: Alterar o Modelo

```python
# backend/app/models/healthcare.py

class MedicalAppointment(Base):
    # ... outros campos ...
    
    # ANTES:
    # appointment_date = Column(DateTime(timezone=True), nullable=False)
    
    # DEPOIS:
    appointment_date = Column(DateTime(timezone=False), nullable=False)
    next_appointment = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### Passo 2: Criar Migration

```sql
-- backend/migrations/remove_timezone.sql

-- Alterar colunas de TIMESTAMP WITH TIME ZONE para TIMESTAMP WITHOUT TIME ZONE
ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN appointment_date TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN next_appointment TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalappointment 
    ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- Repetir para outras tabelas com datetime
ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN procedure_date TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE healthcare_medicalprocedure 
    ALTER COLUMN next_procedure_date TYPE TIMESTAMP WITHOUT TIME ZONE;
```

#### Passo 3: Aplicar Migration

```powershell
# Aplicar no banco local
docker exec -it sistema-postgres psql -U sistema_user -d sistema_db -f /path/to/remove_timezone.sql

# OU se estiver em dev local:
psql -U sistema_user -d sistema_db -f backend/migrations/remove_timezone.sql
```

#### Passo 4: Reiniciar Backend

```powershell
.\stop.ps1
.\start.ps1
```

---

### Abordagem 2: Correção no Schema Pydantic (ALTERNATIVA)

Se não quiser alterar o banco, pode forçar a serialização no Pydantic:

```python
# backend/app/schemas/healthcare.py

from pydantic import BaseModel, field_serializer
from datetime import datetime
from typing import Optional

class MedicalAppointment(MedicalAppointmentBase):
    id: int
    family_member_id: int
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('appointment_date', 'next_appointment', 'created_at', 'updated_at')
    def serialize_naive(self, dt: Optional[datetime]) -> Optional[str]:
        """Remove timezone antes de serializar"""
        if dt is None:
            return None
        # Se tem timezone, remover
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None).isoformat()
        return dt.isoformat()
    
    class Config:
        from_attributes = True
```

**IMPORTANTE**: Esta abordagem não funcionou nas tentativas anteriores, possivelmente porque o FastAPI estava bypassando o serializer.

---

### Abordagem 3: Correção no Frontend (WORKAROUND)

Modificar `formatDateTimeBR` para NÃO usar `new Date()`:

```typescript
// frontend/src/utils/dateUtils.ts

export const formatDateTimeBR = (dateString: string | null | undefined): string => {
  if (!dateString) return '-'
  
  // SEMPRE extrair diretamente da string, NUNCA usar new Date()
  const cleaned = dateString.replace(/[+-]\d{2}:\d{2}$/, '').replace(/Z$/, '')
  const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/)
  
  if (match) {
    const [, year, month, day, hours, minutes] = match
    return `${day}/${month}/${year} ${hours}:${minutes}`
  }
  
  return '-' // Não usar fallback com new Date()
}
```

**NOTA**: Esta abordagem foi implementada mas o problema persiste, indicando que o backend está enviando o timezone na string.

---

## 🎯 RECOMENDAÇÃO FINAL

### Para Resolver DEFINITIVAMENTE:

1. **Aplicar Abordagem 1** (modificar modelo + migration)
2. **Validar** que o banco não tem mais timezone
3. **Reiniciar** completamente o sistema
4. **Testar** criando uma NOVA consulta

### Comando Único para Aplicar Tudo:

```powershell
# 1. Backup do banco
docker exec sistema-postgres pg_dump -U sistema_user sistema_db > backup_antes_fix.sql

# 2. Aplicar SQL (você precisará copiar o arquivo para dentro do container)
docker cp backend/migrations/remove_timezone.sql sistema-postgres:/tmp/
docker exec -it sistema-postgres psql -U sistema_user -d sistema_db -f /tmp/remove_timezone.sql

# 3. Reiniciar
.\stop.ps1
.\start.ps1

# 4. Testar
# Criar uma nova consulta e verificar se mostra o horário correto
```

---

## 📝 O QUE FOI TENTADO (SEM SUCESSO)

Durante esta sessão, foram tentadas as seguintes abordagens:

1. ❌ Configuração de timezone em Docker (todos os containers)
2. ❌ Modificação de `TZ` nos scripts PowerShell
3. ❌ Criação de funções helper (`datetime_to_naive_iso`)
4. ❌ Retorno via `JSONResponse` (bypass Pydantic)
5. ❌ Field serializers no schema Pydantic
6. ❌ Múltiplos reinícios completos do sistema
7. ❌ Criação de endpoint de teste separado
8. ❌ Modificação da função `formatDateTimeBR` no frontend

**Conclusão**: O problema é estrutural e requer modificação no banco de dados.

---

## ⚠️ IMPORTANTE

- **NÃO aplicar em produção sem backup!**
- **Testar primeiro em desenvolvimento**
- **Validar TODAS as telas** que exibem datas após a modificação
- **Considerar criar dados de teste** para validação

---

## 🆘 SUPORTE

Se após aplicar a solução o problema persistir:

1. Verificar no PostgreSQL:
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'healthcare_medicalappointment' 
   AND column_name LIKE '%date%';
   ```

2. Verificar logs do backend para ver como o datetime está sendo carregado

3. Testar endpoint direto:
   ```bash
   curl -H "Authorization: Bearer TOKEN" http://localhost:8001/api/v1/healthcare/appointments
   ```

---

**Data**: 28/11/2025  
**Sessão**: Extensa (150k+ tokens)  
**Status**: Problema identificado, solução documentada, aguardando aplicação

