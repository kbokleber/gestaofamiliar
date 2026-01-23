# Migração de Timezone - São Paulo

## 🎯 Objetivo

Configurar todos os containers Docker para usar o timezone de São Paulo (America/Sao_Paulo) para resolver problemas de comparação de datas entre timezones diferentes.

## 📋 O Que Foi Alterado

### 1. **docker-compose.yml** (Desenvolvimento)
✅ Adicionada variável `TZ: America/Sao_Paulo` em todos os serviços
✅ Configurado `PGTZ: America/Sao_Paulo` no PostgreSQL

### 2. **docker-stack.yml** (Produção)
✅ Adicionada variável `TZ: America/Sao_Paulo` no backend e frontend

### 3. **Dockerfiles**
✅ **backend/Dockerfile**: Instalado `tzdata` e configurado timezone
✅ **frontend/Dockerfile**: Instalado `tzdata` e configurado timezone

### 4. **Backend - Código Python**
✅ **security.py**: Substituído `datetime.utcnow()` (deprecated) por `datetime.now(timezone.utc)`
✅ Mantido uso de UTC para armazenamento no banco (best practice)
✅ Container com timezone de São Paulo faz conversões automaticamente

### 5. **Frontend - Código JavaScript/TypeScript**
✅ **dateUtils.ts**: Já tinha funções que evitam problemas de timezone
✅ Funções extraem data diretamente da string ISO, sem conversão de timezone
✅ Comparações de data usam `isFutureDateTime()` que compara localmente

## 🔄 Como Aplicar as Mudanças

### Desenvolvimento (docker-compose)
```powershell
# Windows PowerShell
.\aplicar-timezone.ps1

# OU manualmente:
docker-compose down
docker-compose up -d --build
```

### Produção (docker swarm)
```bash
# No servidor Linux
cd /opt/sistema-familiar

# Fazer pull das alterações
git pull origin master

# Executar redeploy
chmod +x redeploy-seguro.sh
./redeploy-seguro.sh
```

## ✅ Testar Configuração

### Windows (Desenvolvimento)
```powershell
.\testar-timezone.ps1
```

### Linux (Produção)
```bash
# Backend
docker exec <container-backend> date
docker exec <container-backend> python -c "import datetime; print(datetime.datetime.now())"

# Frontend
docker exec <container-frontend> date

# PostgreSQL (se local)
docker exec <container-db> psql -U postgres -c "SHOW timezone;"
docker exec <container-db> date
```

## 🐛 Problemas Resolvidos

### Antes (Problemas)
❌ Datas salvam em UTC mas exibição esperava timezone local
❌ Comparações entre datas falhavam devido a diferença de timezone
❌ Consultas "futuras" apareciam como "passadas" ou vice-versa
❌ Filtros por data retornavam resultados incorretos

### Agora (Soluções)
✅ Container rodando em timezone de São Paulo (America/Sao_Paulo)
✅ Backend salva em UTC (best practice) mas conversões são automáticas
✅ Frontend extrai datas diretamente da string ISO, sem conversão
✅ Comparações de data funcionam corretamente
✅ Filtros por data retornam resultados esperados

## 🔍 Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────┐
│ BANCO DE DADOS (PostgreSQL)                             │
│ - Timezone: America/Sao_Paulo (PGTZ)                    │
│ - Armazena: TIMESTAMP WITH TIME ZONE em UTC             │
│ - Converte automaticamente na leitura/escrita           │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI/Python)                                │
│ - Container TZ: America/Sao_Paulo                       │
│ - Código usa: datetime.now(timezone.utc)                │
│ - SQLAlchemy usa: DateTime(timezone=True)               │
│ - Conversões automáticas entre UTC e local              │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│ FRONTEND (React/TypeScript)                             │
│ - Container TZ: America/Sao_Paulo                       │
│ - dateUtils extrai datas sem conversão de timezone      │
│ - Comparações usam valores locais                       │
│ - Exibição em formato brasileiro (DD/MM/YYYY)           │
└─────────────────────────────────────────────────────────┘
```

## 📝 Detalhes Técnicos

### Backend - Models
Todos os campos de data/hora usam `DateTime(timezone=True)`:
```python
created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
appointment_date = Column(DateTime(timezone=True), nullable=False)
```

### Backend - Criação de Registros
Usa `datetime.now(timezone.utc)` para garantir timezone aware:
```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
record['created_at'] = now
record['updated_at'] = now
```

### Frontend - Formatação
Funções em `dateUtils.ts` extraem datas da string ISO sem conversão:
```typescript
// Extrai diretamente da string, sem new Date()
const match = dateString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/)
if (match) {
  const [, year, month, day, hours, minutes] = match
  return `${day}/${month}/${year} ${hours}:${minutes}`
}
```

### Frontend - Comparações
Função `isFutureDateTime()` compara valores locais:
```typescript
// Extrai valores da string ISO
const appointmentDate = new Date(year, month-1, day, hours, minutes)
const now = new Date()
return appointmentDate > now
```

## ⚠️ Importante para Desenvolvedores

### Ao Criar Novos Campos de Data/Hora

**Backend:**
- Sempre use `DateTime(timezone=True)` nos models
- Use `datetime.now(timezone.utc)` ao criar registros
- Nunca use `datetime.utcnow()` (deprecated)

**Frontend:**
- Use funções de `dateUtils.ts` para formatação
- Evite `new Date()` com strings ISO diretamente
- Para comparações, use `isFutureDateTime()` ou extraia valores manualmente

### Ao Filtrar por Data

**Backend:**
- Os filtros funcionam automaticamente com timezone aware dates

**Frontend:**
- Use `new Date(filterDate)` para comparações
- Ajuste hora para início (00:00:00) ou fim do dia (23:59:59)
- Veja exemplos em `Appointments.tsx`, `MaintenanceOrders.tsx`, etc.

## 🚀 Benefícios

1. **Consistência**: Todos os containers usam o mesmo timezone
2. **Precisão**: Datas são exibidas corretamente no horário de São Paulo
3. **Confiabilidade**: Comparações de data funcionam como esperado
4. **Manutenibilidade**: Código mais claro e fácil de entender
5. **Best Practice**: Armazenamento em UTC, exibição em timezone local
6. **Persistência**: Configurações sobrevivem a redeploys

## 📚 Referências

- [PostgreSQL Timezone](https://www.postgresql.org/docs/current/datatype-datetime.html)
- [Python datetime with timezone](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects)
- [Docker timezone configuration](https://docs.docker.com/engine/reference/builder/#env)
- [JavaScript Date and Timezone](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date)

## 🔄 Rollback (Se Necessário)

Se precisar reverter as mudanças:

```bash
# Dev (Windows)
git checkout HEAD~1 docker-compose.yml backend/Dockerfile frontend/Dockerfile
docker-compose down && docker-compose up -d --build

# Prod (Linux)
cd /opt/sistema-familiar
git checkout HEAD~1 docker-stack.yml backend/Dockerfile frontend/Dockerfile
./redeploy-seguro.sh
```

---

**Data da Migração**: 28/11/2025
**Versão**: 1.1
**Status**: ✅ Pronto para Deploy

