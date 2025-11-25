# 🏠 Gestão Familiar 2.0

Sistema completo de gestão familiar com foco em **saúde** e **manutenção de equipamentos**. Desenvolvido com tecnologias modernas e arquitetura escalável.

## 📚 Documentação Completa

**👉 Consulte [DOCUMENTACAO.md](./DOCUMENTACAO.md) para a documentação completa e detalhada.**

A documentação inclui:
- ✅ Instalação e setup local
- ✅ Deploy em VPS
- ✅ Configuração do Nginx Proxy Manager
- ✅ Configuração de banco de dados
- ✅ Comandos úteis
- ✅ Troubleshooting completo
- ✅ Estrutura do projeto

## 📋 Índice Rápido

- [Tecnologias](#-tecnologias)
- [Funcionalidades](#-funcionalidades)
- [Quick Start](#-quick-start)
- [Estrutura do Projeto](#-estrutura-do-projeto)

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

## ⚡ Quick Start

### Setup Automático (Windows)

```powershell
# Execute o script de setup
.\setup.ps1

# Inicie os servidores
.\start.ps1
```

### Setup Manual

1. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   copy .env.example .env
   # Edite o .env com suas configurações
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   ```

3. **Iniciar:**
   ```powershell
   .\start.ps1
   ```

4. **Acessar:**
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8001
   - API Docs: http://localhost:8001/api/v1/docs

**📖 Para instruções detalhadas, consulte [DOCUMENTACAO.md](./DOCUMENTACAO.md)**

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

Para troubleshooting completo, consulte a seção **Troubleshooting** em [DOCUMENTACAO.md](./DOCUMENTACAO.md).

**Problemas comuns:**
- Erro 502 Bad Gateway → Ver seção de Troubleshooting na documentação
- Erro ao conectar no PostgreSQL → Verificar configuração do banco
- Erro de CORS → Verificar se backend está rodando
- Port já em uso → Parar processos ou mudar porta

---

**📚 Consulte [DOCUMENTACAO.md](./DOCUMENTACAO.md) para informações completas sobre:**
- ✅ Instalação detalhada
- ✅ Deploy em VPS
- ✅ Configuração do Nginx Proxy Manager
- ✅ Troubleshooting completo
- ✅ Comandos úteis
- ✅ Estrutura do projeto

**🎉 Pronto! Seu Sistema Familiar está configurado e funcionando!**

