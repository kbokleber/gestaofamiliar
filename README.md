# 🏠 Sistema Familiar 2.0

Sistema completo de gestão familiar com foco em **saúde** e **manutenção de equipamentos**. Desenvolvido com tecnologias modernas e arquitetura escalável.

## 📋 Índice

- [Tecnologias](#-tecnologias)
- [Funcionalidades](#-funcionalidades)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Execução](#-execução)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API Documentation](#-api-documentation)

## 🚀 Tecnologias

### Backend
- **FastAPI** - Framework web moderno e rápido para Python
- **SQLAlchemy** - ORM para Python
- **PostgreSQL** - Banco de dados relacional
- **JWT** - Autenticação com tokens
- **Pydantic** - Validação de dados

### Frontend
- **React** - Biblioteca para interfaces
- **TypeScript** - JavaScript com tipagem
- **Vite** - Build tool ultra-rápido
- **TailwindCSS** - Framework CSS utility-first
- **React Router** - Navegação
- **Axios** - Cliente HTTP
- **Zustand** - Gerenciamento de estado
- **React Query** - Cache e sincronização de dados
- **PWA** - Progressive Web App (funciona offline e pode ser instalado)

## ✨ Funcionalidades

### 👨‍👩‍👧‍👦 Módulo de Saúde (Healthcare)
- ✅ Cadastro de membros da família
- ✅ Registro de consultas médicas
- ✅ Controle de medicamentos
- ✅ Histórico de procedimentos médicos
- ✅ Alertas de medicação
- ✅ Fotos de perfil dos membros

### 🔧 Módulo de Manutenção (Maintenance)
- ✅ Cadastro de equipamentos domésticos
- ✅ Registro de ordens de manutenção
- ✅ Histórico de manutenções
- ✅ Controle de garantias
- ✅ Upload de notas fiscais e anexos
- ✅ Estatísticas de custos

### 🔐 Sistema de Autenticação
- ✅ Login/Registro de usuários
- ✅ Autenticação JWT
- ✅ Perfis de usuário
- ✅ Controle de acesso

## 📦 Requisitos

- **Python** 3.10+
- **Node.js** 18+
- **PostgreSQL** 14+
- **npm** ou **yarn**

## 🛠 Instalação

### 1. Clone o repositório

\`\`\`bash
git clone <repository-url>
cd SistemaFamiliar2.0
\`\`\`

### 2. Configure o PostgreSQL

Certifique-se de que o PostgreSQL está rodando e crie o banco de dados:

\`\`\`sql
CREATE DATABASE sistema_familiar_db;
CREATE USER sistema_familiar_user WITH PASSWORD 'SuaSenhaSeguraParaDB2024#';
GRANT ALL PRIVILEGES ON DATABASE sistema_familiar_db TO sistema_familiar_user;
\`\`\`

**Ou use o Docker Compose do projeto antigo:**

\`\`\`bash
cd "C:\\Projetos\\Sistema Familiar"
docker-compose up -d db
\`\`\`

### 3. Backend Setup

\`\`\`bash
cd backend

# Criar ambiente virtual (Windows)
python -m venv venv
.\\venv\\Scripts\\activate

# Instalar dependências
pip install -r requirements.txt

# Criar arquivo .env
copy .env.example .env
# Edite o .env com suas configurações
\`\`\`

**Importante:** Edite o arquivo `.env` com suas credenciais do PostgreSQL e gere uma SECRET_KEY segura:

\`\`\`env
DATABASE_URL=postgresql://sistema_familiar_user:SuaSenhaSeguraParaDB2024#@localhost:5432/sistema_familiar_db
SECRET_KEY=gere-uma-chave-secreta-aqui
\`\`\`

### 4. Frontend Setup

\`\`\`bash
cd frontend

# Instalar dependências
npm install

# Adicionar dependência faltante
npm install tailwindcss-animate

# Criar arquivo .env
copy .env.example .env.local
\`\`\`

## ⚙️ Configuração

### Migração do Banco de Dados

Como você já tem um banco de dados existente do Django, a estrutura das tabelas já está criada. O SQLAlchemy irá se conectar às tabelas existentes.

**Se precisar criar as tabelas do zero:**

\`\`\`bash
cd backend
# Criar arquivo de migração (opcional)
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
\`\`\`

**Ou via Python:**

\`\`\`python
from app.db.base import engine
from app.models import *

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)
\`\`\`

### Criar Super Usuário (Opcional)

\`\`\`python
# backend/create_admin.py
from app.db.base import SessionLocal
from app.models.user import User, Profile
from app.core.security import get_password_hash

db = SessionLocal()

admin = User(
    username="admin",
    email="admin@sistemafamiliar.com",
    password=get_password_hash("admin123"),
    first_name="Admin",
    last_name="Sistema",
    is_active=True,
    is_staff=True,
    is_superuser=True
)

db.add(admin)
db.commit()
db.refresh(admin)

# Criar perfil
profile = Profile(user_id=admin.id)
db.add(profile)
db.commit()

print(f"Admin criado: {admin.username}")
\`\`\`

Execute:

\`\`\`bash
cd backend
python create_admin.py
\`\`\`

## 🚀 Execução

### Desenvolvimento Local

**Terminal 1 - Backend:**

\`\`\`bash
cd backend
.\\venv\\Scripts\\activate  # Windows
# source venv/bin/activate  # Linux/Mac

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

O backend estará disponível em:
- **API:** http://localhost:8001
- **Documentação interativa (Swagger):** http://localhost:8001/api/v1/docs
- **ReDoc:** http://localhost:8001/api/v1/redoc

**Terminal 2 - Frontend:**

\`\`\`bash
cd frontend
npm run dev
\`\`\`

O frontend estará disponível em: **http://localhost:5173**

### Build para Produção

**Backend:**

\`\`\`bash
cd backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
\`\`\`

**Frontend:**

\`\`\`bash
cd frontend
npm run build
# Os arquivos estarão em: frontend/dist
\`\`\`

Para servir o build:

\`\`\`bash
npm install -g serve
serve -s dist -p 5173
\`\`\`

## 📁 Estrutura do Projeto

\`\`\`
SistemaFamiliar2.0/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py           # Autenticação (login/register)
│   │   │   │   │   ├── users.py          # Usuários
│   │   │   │   │   ├── dashboard.py      # Dashboard e preferências
│   │   │   │   │   ├── healthcare.py     # Saúde (membros, consultas, medicamentos)
│   │   │   │   │   └── maintenance.py    # Manutenção (equipamentos, ordens)
│   │   │   │   └── api.py                # Agregador de rotas
│   │   │   └── deps.py                   # Dependências (get_current_user)
│   │   ├── core/
│   │   │   ├── config.py                 # Configurações (settings)
│   │   │   └── security.py               # JWT e criptografia
│   │   ├── db/
│   │   │   └── base.py                   # Conexão com PostgreSQL
│   │   ├── models/
│   │   │   ├── user.py                   # User, Profile
│   │   │   ├── dashboard.py              # DashboardPreference
│   │   │   ├── healthcare.py             # FamilyMember, Appointment, Medication, Procedure
│   │   │   └── maintenance.py            # Equipment, MaintenanceOrder, Attachment, Image
│   │   ├── schemas/
│   │   │   └── ...                       # Schemas Pydantic para validação
│   │   └── main.py                       # Aplicação FastAPI
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.tsx                # Layout principal com sidebar
│   │   ├── lib/
│   │   │   ├── api.ts                    # Cliente Axios configurado
│   │   │   └── utils.ts                  # Utilitários
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx             # Página inicial
│   │   │   ├── Login.tsx                 # Login
│   │   │   ├── Register.tsx              # Registro
│   │   │   ├── healthcare/
│   │   │   │   ├── FamilyMembers.tsx
│   │   │   │   ├── Appointments.tsx
│   │   │   │   └── Medications.tsx
│   │   │   └── maintenance/
│   │   │       ├── Equipment.tsx
│   │   │       └── MaintenanceOrders.tsx
│   │   ├── services/
│   │   │   └── authService.ts            # Serviços de autenticação
│   │   ├── stores/
│   │   │   └── authStore.ts              # Zustand store para auth
│   │   ├── App.tsx                       # Rotas principais
│   │   ├── main.tsx                      # Entry point
│   │   └── index.css                     # Estilos globais + Tailwind
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
└── README.md
\`\`\`

## 📚 API Documentation

Após iniciar o backend, acesse a documentação interativa:

- **Swagger UI:** http://localhost:8001/api/v1/docs
- **ReDoc:** http://localhost:8001/api/v1/redoc

### Principais Endpoints

#### Autenticação
- \`POST /api/v1/auth/login\` - Login
- \`POST /api/v1/auth/register\` - Registro

#### Usuários
- \`GET /api/v1/users/me\` - Obter usuário atual
- \`PUT /api/v1/users/me/profile\` - Atualizar perfil

#### Healthcare
- \`GET /api/v1/healthcare/members\` - Listar membros
- \`POST /api/v1/healthcare/members\` - Criar membro
- \`GET /api/v1/healthcare/appointments\` - Listar consultas
- \`POST /api/v1/healthcare/appointments\` - Criar consulta
- \`GET /api/v1/healthcare/medications\` - Listar medicamentos
- \`POST /api/v1/healthcare/medications\` - Criar medicamento

#### Maintenance
- \`GET /api/v1/maintenance/equipment\` - Listar equipamentos
- \`POST /api/v1/maintenance/equipment\` - Criar equipamento
- \`GET /api/v1/maintenance/orders\` - Listar ordens de manutenção
- \`POST /api/v1/maintenance/orders\` - Criar ordem
- \`GET /api/v1/maintenance/dashboard/stats\` - Estatísticas

## 🎨 PWA (Progressive Web App)

O frontend é uma PWA, o que significa:

- ✅ Pode ser instalado como app no celular/desktop
- ✅ Funciona offline (cache de dados)
- ✅ Ícone na tela inicial
- ✅ Notificações push (futuro)

Para instalar:
1. Acesse pelo navegador mobile
2. Clique em "Adicionar à tela inicial"
3. Use como um app nativo!

## 🔒 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ Autenticação JWT
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ Proteção contra SQL Injection (SQLAlchemy ORM)
- ✅ Tokens expiram em 30 minutos

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (\`git checkout -b feature/AmazingFeature\`)
3. Commit suas mudanças (\`git commit -m 'Add some AmazingFeature'\`)
4. Push para a branch (\`git push origin feature/AmazingFeature\`)
5. Abra um Pull Request

## 📝 Licença

Este projeto é privado e de uso familiar.

## 👨‍💻 Autor

Desenvolvido com ❤️ para gestão familiar

---

## 🚨 Troubleshooting

### Erro ao conectar no PostgreSQL

Verifique se:
1. O PostgreSQL está rodando
2. As credenciais no `.env` estão corretas
3. O banco de dados foi criado
4. O firewall não está bloqueando a porta 5432

### Erro de CORS no frontend

Verifique se o backend está rodando e se o CORS está configurado corretamente em `backend/app/main.py`.

### Dependências não encontradas

Execute novamente:
- Backend: \`pip install -r requirements.txt\`
- Frontend: \`npm install\`

### Port já em uso

Mude a porta no comando de execução:
- Backend: \`uvicorn app.main:app --reload --port 8001\`
- Frontend: \`vite --port 5174\`

---

**🎉 Pronto! Seu Sistema Familiar está configurado e funcionando!**

