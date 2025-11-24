# 🚀 Setup Rápido - Sistema Familiar 2.0

## ⚡ Instalação Rápida (5 minutos)

### 1. Execute o script de setup automático:

```powershell
.\setup.ps1
```

Este script irá:
- ✅ Verificar Python, Node.js e PostgreSQL
- ✅ Criar ambiente virtual Python
- ✅ Instalar todas as dependências do backend
- ✅ Instalar todas as dependências do frontend

### 2. Configure a conexão com o banco de dados PostgreSQL existente

O backend já está configurado para usar seu banco PostgreSQL existente!

Verifique o arquivo `backend/.env`:

```env
DATABASE_URL=postgresql://sistema_familiar_user:SuaSenhaSeguraParaDB2024#@localhost:5432/sistema_familiar_db
```

**Se o banco estiver em Docker:**
- Host: `localhost` (ou `db` se estiver dentro do container)
- Port: `5432`
- Database: `sistema_familiar_db`
- User: `sistema_familiar_user`
- Password: `SuaSenhaSeguraParaDB2024#`

### 3. Criar usuário administrador (opcional)

```powershell
cd backend
.\venv\Scripts\activate
python create_admin.py
```

Isso criará:
- **Username:** admin
- **Password:** admin123
- **Email:** admin@sistemafamiliar.com

### 4. Inicie os servidores

**Opção A - Script automático (recomendado):**

```powershell
.\start.ps1
```

Isso abrirá 2 janelas do PowerShell, uma para cada servidor.

**Opção B - Manual:**

Terminal 1 (Backend):
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

Terminal 2 (Frontend):
```powershell
cd frontend
npm run dev
```

### 5. Acesse a aplicação

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8001
- **Documentação Interativa:** http://localhost:8001/api/v1/docs

## 🎯 Compatibilidade com Banco Django Existente

O backend FastAPI foi desenvolvido para ser **100% compatível** com o banco de dados do seu sistema Django existente:

✅ **Mesmos nomes de tabelas:**
- `auth_user` (usuários do Django)
- `accounts_profile`
- `healthcare_familymember`
- `healthcare_medicalappointment`
- `healthcare_medicalprocedure`
- `healthcare_medication`
- `maintenance_equipment`
- `maintenance_maintenanceorder`
- `maintenance_equipmentattachment`
- `maintenance_maintenanceimage`
- `dashboard_dashboardpreference`

✅ **Mesmas colunas e tipos de dados**

✅ **Mesmos relacionamentos (FKs)**

✅ **Você pode usar ambos os sistemas simultaneamente!**

### Migração de Dados

Não é necessária! O FastAPI irá:
- ✅ Ler os dados existentes
- ✅ Criar novos registros compatíveis
- ✅ Atualizar registros existentes
- ✅ Funcionar em paralelo com o Django

## 🔐 Primeiro Acesso

Se você já tem usuários no banco Django, pode fazer login com as mesmas credenciais!

**Se não:**

1. Crie um admin com o script: `python backend/create_admin.py`
2. Ou registre-se pela interface: http://localhost:5173/register

## 🛠️ Comandos Úteis

### Backend

```powershell
# Ativar ambiente virtual
cd backend
.\venv\Scripts\activate

# Rodar servidor
uvicorn app.main:app --reload

# Criar admin
python create_admin.py

# Verificar conexão com banco
python -c "from app.db.base import engine; print(engine.connect())"
```

### Frontend

```powershell
cd frontend

# Rodar dev server
npm run dev

# Build para produção
npm run build

# Preview do build
npm run preview
```

## 🐛 Troubleshooting

### ❌ Erro ao conectar no PostgreSQL

**Problema:** `could not connect to server`

**Solução:**
1. Verifique se o PostgreSQL está rodando
2. Se estiver em Docker: `docker-compose up -d db`
3. Teste a conexão:
   ```powershell
   psql -h localhost -U sistema_familiar_user -d sistema_familiar_db
   ```

### ❌ Módulo não encontrado

**Problema:** `ModuleNotFoundError`

**Solução:**
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

### ❌ Porta já em uso

**Problema:** `Address already in use`

**Solução:**
- Backend: Mude a porta: `uvicorn app.main:app --reload --port 8001`
- Frontend: Mude a porta: `npm run dev -- --port 5174`

### ❌ CORS Error no frontend

**Problema:** Requisições bloqueadas pelo CORS

**Solução:** Verifique se o backend está rodando e se o CORS está configurado em `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📱 PWA - Instalar como App

1. Acesse pelo navegador mobile: http://[seu-ip]:5173
2. Clique em "Adicionar à tela inicial"
3. Use como um app nativo!

## 🎉 Pronto!

Seu Sistema Familiar está funcionando! 

- ✅ Backend FastAPI conectado ao PostgreSQL
- ✅ Frontend React moderno e responsivo
- ✅ Compatível com dados Django existentes
- ✅ PWA instalável
- ✅ Documentação automática da API

---

**Problemas?** Consulte o README.md completo na raiz do projeto.

