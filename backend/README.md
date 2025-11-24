# Backend - Sistema Familiar

API RESTful construída com FastAPI para o Sistema Familiar.

## 🚀 Quick Start

\`\`\`bash
# Ativar ambiente virtual
.\\venv\\Scripts\\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
copy .env.example .env
# Edite o .env com suas configurações

# Rodar servidor
uvicorn app.main:app --reload
\`\`\`

## 📦 Dependências Principais

- **FastAPI** - Framework web
- **SQLAlchemy** - ORM
- **Pydantic** - Validação
- **python-jose** - JWT
- **passlib** - Hash de senhas
- **psycopg2** - Driver PostgreSQL
- **uvicorn** - Servidor ASGI

## 🗄️ Models

### User & Profile
- `auth_user` - Usuários do sistema (compatível com Django)
- `accounts_profile` - Perfis estendidos

### Healthcare
- `healthcare_familymember` - Membros da família
- `healthcare_medicalappointment` - Consultas médicas
- `healthcare_medicalprocedure` - Procedimentos
- `healthcare_medication` - Medicamentos

### Maintenance
- `maintenance_equipment` - Equipamentos
- `maintenance_maintenanceorder` - Ordens de manutenção
- `maintenance_equipmentattachment` - Anexos
- `maintenance_maintenanceimage` - Imagens

### Dashboard
- `dashboard_dashboardpreference` - Preferências do usuário

## 🔐 Autenticação

A API usa JWT (JSON Web Tokens). Para autenticar:

1. **Registrar:** \`POST /api/v1/auth/register\`
2. **Login:** \`POST /api/v1/auth/login\`
3. **Usar token:** Adicione header \`Authorization: Bearer <token>\`

## 📡 Endpoints

Documentação completa em: http://localhost:8000/api/v1/docs

## 🛠️ Desenvolvimento

### Adicionar um novo modelo

1. Criar arquivo em \`app/models/\`
2. Importar em \`app/models/__init__.py\`
3. Criar schemas em \`app/schemas/\`
4. Criar endpoints em \`app/api/v1/endpoints/\`
5. Registrar router em \`app/api/v1/api.py\`

### Estrutura de um endpoint

\`\`\`python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/items")
async def list_items(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Sua lógica aqui
    return items
\`\`\`

## 🧪 Testes

\`\`\`bash
pip install pytest pytest-cov
pytest
\`\`\`

## 🚀 Deploy

\`\`\`bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
\`\`\`

