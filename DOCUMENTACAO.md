# 📚 Documentação Completa - Gestão Familiar 2.0

Sistema completo de gestão familiar com foco em **saúde** e **manutenção de equipamentos**. Desenvolvido com tecnologias modernas e arquitetura escalável.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Instalação e Setup Local](#instalação-e-setup-local)
3. [Deploy em VPS](#deploy-em-vps)
4. [Configuração do Nginx Proxy Manager](#configuração-do-nginx-proxy-manager)
5. [Configuração de Banco de Dados](#configuração-de-banco-de-dados)
6. [Comandos Úteis](#comandos-úteis)
7. [Troubleshooting](#troubleshooting)
8. [Estrutura do Projeto](#estrutura-do-projeto)

---

## 🚀 Visão Geral

### Tecnologias

**Backend:**
- FastAPI - Framework web moderno e rápido para Python
- SQLAlchemy - ORM para Python
- PostgreSQL - Banco de dados relacional
- JWT - Autenticação com tokens
- Pydantic - Validação de dados

**Frontend:**
- React - Biblioteca para interfaces
- TypeScript - JavaScript com tipagem
- Vite - Build tool ultra-rápido
- TailwindCSS - Framework CSS utility-first
- React Router - Navegação
- Axios - Cliente HTTP
- Zustand - Gerenciamento de estado
- PWA - Progressive Web App (funciona offline e pode ser instalado)

### Funcionalidades

**Módulo de Saúde (Healthcare):**
- ✅ Cadastro de membros da família
- ✅ Registro de consultas médicas
- ✅ Controle de medicamentos
- ✅ Histórico de procedimentos médicos
- ✅ Alertas de medicação
- ✅ Fotos de perfil dos membros

**Módulo de Manutenção (Maintenance):**
- ✅ Cadastro de equipamentos domésticos
- ✅ Registro de ordens de manutenção
- ✅ Histórico de manutenções
- ✅ Controle de garantias
- ✅ Upload de notas fiscais e anexos
- ✅ Estatísticas de custos

**Sistema de Autenticação:**
- ✅ Login/Registro de usuários
- ✅ Autenticação JWT
- ✅ Perfis de usuário
- ✅ Controle de acesso
- ✅ Administração de usuários

---

## 🛠️ Instalação e Setup Local

### Pré-requisitos

- **Python** 3.10+
- **Node.js** 18+
- **PostgreSQL** 14+
- **npm** ou **yarn**

### Setup Rápido

#### 1. Clone o repositório

```bash
git clone <repository-url>
cd SistemaFamiliar2.0
```

#### 2. Configure o PostgreSQL

Certifique-se de que o PostgreSQL está rodando e crie o banco de dados:

```sql
CREATE DATABASE sistema_familiar_db;
CREATE USER sistema_familiar_user WITH PASSWORD 'SuaSenhaSeguraParaDB2024#';
GRANT ALL PRIVILEGES ON DATABASE sistema_familiar_db TO sistema_familiar_user;
```

**Ou use o Docker Compose do projeto antigo:**

```bash
cd "C:\Projetos\Sistema Familiar"
docker-compose up -d db
```

#### 3. Backend Setup

```bash
cd backend

# Criar ambiente virtual (Windows)
python -m venv venv
.\venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Criar arquivo .env
copy .env.example .env
# Edite o .env com suas configurações
```

**Importante:** Edite o arquivo `.env` com suas credenciais do PostgreSQL:

```env
DATABASE_URL=postgresql://sistema_familiar_user:SuaSenhaSeguraParaDB2024#@localhost:5432/sistema_familiar_db
SECRET_KEY=gere-uma-chave-secreta-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Gerar SECRET_KEY:**
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

#### 4. Frontend Setup

```bash
cd frontend

# Instalar dependências
npm install

# Criar arquivo .env.local (opcional)
# VITE_API_URL=http://localhost:8001/api/v1
```

#### 5. Criar Usuário Administrador (Opcional)

```bash
cd backend
.\venv\Scripts\activate
python create_admin.py
```

Isso criará:
- **Username:** admin
- **Password:** admin123
- **Email:** admin@sistemafamiliar.com

#### 6. Iniciar Servidores

**Opção A - Script automático (recomendado):**

```powershell
.\start.ps1
```

**Opção B - Manual:**

Terminal 1 (Backend):
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Terminal 2 (Frontend):
```powershell
cd frontend
npm run dev
```

#### 7. Acessar a Aplicação

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8001
- **Documentação Interativa (Swagger):** http://localhost:8001/api/v1/docs
- **ReDoc:** http://localhost:8001/api/v1/redoc

### Scripts PowerShell Disponíveis

- `.\start.ps1` - Inicia backend e frontend
- `.\start-backend.ps1` - Inicia apenas backend
- `.\start-frontend.ps1` - Inicia apenas frontend
- `.\stop.ps1` - Para backend e frontend
- `.\status.ps1` - Verifica status dos serviços
- `.\setup.ps1` - Setup automático completo

### Compatibilidade com Banco Django Existente

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

✅ **Você pode usar ambos os sistemas simultaneamente!**

---

## 🚀 Deploy em VPS

### Pré-requisitos

- ✅ VPS com Docker e Docker Swarm instalados
- ✅ Acesso SSH ao servidor
- ✅ PostgreSQL rodando em Docker (rede: `db_network`)
- ✅ Nginx Proxy Manager rodando em Docker (rede: `nginx_public`)
- ✅ Domínio configurado (opcional, mas recomendado)

### Passo 1: Preparar o Código Localmente

```powershell
# No seu computador Windows
cd C:\Projetos\SistemaFamiliar2.0
git status

# Se houver alterações, fazer commit
git add .
git commit -m "Preparando para deploy"
git push
```

### Passo 2: Enviar Código para o Servidor

**Opção A: Usando Git (Recomendado)**

```bash
# Conectar ao servidor via SSH
ssh usuario@seu-servidor-ip

# Criar diretório para o projeto
mkdir -p /opt/sistema-familiar
cd /opt/sistema-familiar

# Clonar o repositório
git clone https://github.com/kbokleber/gestaofamiliar.git .

# Ou se já existe, fazer pull
cd /opt/sistema-familiar
git pull
```

**Opção B: Usando SCP**

```powershell
# No seu computador Windows (PowerShell)
scp -r C:\Projetos\SistemaFamiliar2.0\* usuario@seu-servidor-ip:/opt/sistema-familiar/
```

### Passo 3: Configurar Variáveis de Ambiente

```bash
# No servidor
cd /opt/sistema-familiar
cp .env.example .env
nano .env  # ou use vi, vim, ou outro editor
```

**Preencher o arquivo `.env`:**

```env
# BANCO DE DADOS
# Formato: postgresql://usuario:senha@host:porta/database
# Se o banco está em outro container Docker, use o nome do serviço ou IP
DATABASE_URL=postgresql://postgres:senha@nome-container-postgres:5432/sistema_familiar_db

# SEGURANÇA - JWT
# Gere uma chave secreta forte:
# openssl rand -hex 32
SECRET_KEY=sua-chave-secreta-gerada-com-openssl-rand-hex-32

# Algoritmo JWT (padrão)
ALGORITHM=HS256

# Tempo de expiração do token (minutos)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Ambiente
ENVIRONMENT=production
```

**Gerar SECRET_KEY:**

```bash
# No servidor, gere uma chave secreta:
openssl rand -hex 32

# Copie o resultado e cole no .env como SECRET_KEY
```

### Passo 4: Verificar Redes Docker

```bash
# No servidor
docker network ls
```

Você deve ver:
- `db_network` (rede do banco de dados)
- `nginx_public` (rede do Nginx Proxy Manager)

**Se as redes não existirem:**

```bash
# Ver redes do banco de dados
docker inspect nome-container-postgres | grep -A 10 "Networks"

# Ver redes do Nginx
docker inspect nome-container-nginx | grep -A 10 "Networks"

# Ou listar todas as redes
docker network ls
```

Se os nomes forem diferentes, edite o `docker-stack.yml` antes de continuar.

### Passo 5: Construir Imagens e Fazer Deploy

```bash
cd /opt/sistema-familiar

# Dar permissão de execução ao script
chmod +x deploy.sh

# Executar o deploy
./deploy.sh
```

O script irá:
1. ✅ Verificar se Docker Swarm está ativo
2. ✅ Construir as imagens `sistema-familiar-backend:latest` e `sistema-familiar-frontend:latest`
3. ✅ Verificar se o arquivo `.env` está configurado
4. ✅ Verificar se as redes Docker existem
5. ✅ Fazer o deploy do stack

**⏱️ Tempo estimado:** 5-10 minutos

### Passo 6: Verificar Deploy

```bash
# Ver serviços do stack
docker stack services sistema-familiar

# Ver detalhes dos serviços
docker service ps sistema-familiar_backend
docker service ps sistema-familiar_frontend

# Ver logs
docker service logs -f sistema-familiar_backend
docker service logs -f sistema-familiar_frontend

# Verificar se os containers estão rodando
docker ps | grep sistema-familiar
```

### Passo 7: Redeploy do Sistema (Método Recomendado)

**⚠️ IMPORTANTE:** Use o script `redeploy-seguro.sh` para fazer redeploy completo do sistema. Este script garante que:
- As variáveis do `.env` sejam carregadas corretamente
- O stack seja removido de forma segura
- Os serviços sejam redeployados com as configurações corretas
- O backend seja conectado à rede `nginx_public`
- A saúde do backend seja verificada

#### Redeploy Completo (Recomendado)

```bash
cd /opt/sistema-familiar

# 1. Fazer pull das mudanças
git pull origin master

# 2. Dar permissão de execução (se necessário)
chmod +x redeploy-seguro.sh

# 3. Executar redeploy seguro
./redeploy-seguro.sh
```

O script irá:
1. ✅ Verificar se o stack existe
2. ✅ Verificar se as redes externas (`db_network`, `nginx_public`) existem
3. ✅ Remover o stack de forma segura (aguardando remoção completa)
4. ✅ Verificar e carregar variáveis do `.env`
5. ✅ Fazer deploy do stack com as variáveis corretas
6. ✅ Verificar se o backend está na rede `nginx_public`
7. ✅ Verificar a saúde do backend
8. ✅ **Reiniciar o NPM automaticamente para limpar cache** (evita 502 Bad Gateway)

**⏱️ Tempo estimado:** 2-3 minutos

#### Atualizar Apenas Frontend (após mudanças no frontend)

**No Windows (local):**
```powershell
.\rebuild-frontend.ps1
```

**No Linux (VPS):**
```bash
cd /opt/sistema-familiar

# 1. Fazer pull das mudanças
git pull origin master

# 2. Reconstruir apenas frontend
APP_VERSION="$(git show -s --format=%cs HEAD | tr '-' '.')-$(git rev-parse --short HEAD)"
docker build --build-arg VITE_APP_VERSION="${APP_VERSION}" -t sistema-familiar-frontend:latest ./frontend

# 3. Atualizar serviço frontend
docker service update --force --image sistema-familiar-frontend:latest sistema-familiar_frontend
```

**⚠️ IMPORTANTE:** Após atualizar o frontend, limpe o cache do navegador (Ctrl+Shift+R ou Cmd+Shift+R) para ver as mudanças!

#### Atualizar Apenas Backend (após mudanças no backend)

```bash
cd /opt/sistema-familiar

# 1. Fazer pull das mudanças
git pull origin master

# 2. Reconstruir apenas backend
docker build -t sistema-familiar-backend:latest ./backend

# 3. Atualizar serviço backend
docker service update --force --image sistema-familiar-backend:latest sistema-familiar_backend
```

**⚠️ NOTA:** Se houver mudanças no `.env` ou problemas de conectividade, use o `redeploy-seguro.sh` em vez de atualizar apenas o serviço.

---

## 🌐 Configuração do Nginx Proxy Manager

### Configuração Básica

#### 1. Acessar Nginx Proxy Manager

Acesse: `http://seu-servidor-ip:81` e faça login.

#### 2. Configurar Proxy Host para Frontend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `seu-dominio.com` (ou IP do servidor)
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_frontend` ⚠️ **Nome completo do serviço**
   - **Forward Port:** `80` ⚠️ **Porta interna do container**
   - ✅ Marque **"Websockets Support"**
3. Clique em **"Save"**

#### 3. Configurar Proxy Host para Backend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `seu-dominio.com` (mesmo do frontend)
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_backend` ⚠️ **Nome completo do serviço**
   - **Forward Port:** `8001` ⚠️ **Porta interna do container**
   - ✅ Marque **"Websockets Support"**
3. Na aba **"Advanced"**, adicione:

```nginx
# Custom Nginx Configuration
location /api {
    proxy_pass http://sistema-familiar_backend:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

4. Clique em **"Save"**

**⚠️ IMPORTANTE:**
- Use sempre o nome completo do serviço: `sistema-familiar_backend` (não `backend` ou `sistema-familiar-backend`)
- Use a porta interna do container: `8001` (não a porta exposta externamente)
- Frontend usa porta `80` internamente (não `5173`)

### Configurar SSL (Opcional mas Recomendado)

1. Na configuração do Proxy Host, vá na aba **"SSL"**
2. Selecione **"Request a new SSL Certificate"**
3. Marque **"Force SSL"** e **"HTTP/2 Support"**
4. Clique em **"Save"**

### Acessar via IP (sem DNS)

Se você não tiver um domínio configurado, pode acessar via IP:

1. Descobrir o IP do servidor:
   ```bash
   hostname -I
   ```

2. No NPM, configure o Proxy Host com:
   - **Domain Names:** `SEU-IP` (exemplo: `192.168.1.100`)
   - Resto da configuração igual ao acima

3. Acesse: `http://SEU-IP`

### Resolver Problema de Mixed Content (HTTPS → HTTP)

Se você acessar via HTTPS mas o frontend tentar fazer requisições HTTP, o navegador bloqueará (Mixed Content).

**Solução:** Fazer tudo passar pelo NPM via HTTPS usando URLs relativas.

1. O frontend já está configurado para usar URL relativa (`/api/v1`) quando detectar HTTPS
2. Configure o Custom Location `/api` no NPM (veja Passo 3 acima)
3. Certifique-se de que o backend está na rede `nginx_public`

### Resolver Proxy Host Offline

Se o NPM mostrar "Offline":

1. **Verificar se o serviço está rodando:**
   ```bash
   docker service ls | grep sistema-familiar
   docker service ps sistema-familiar_frontend
   ```

2. **Verificar se está na rede correta:**
   ```bash
   docker service inspect sistema-familiar_frontend | grep -A 5 "Networks"
   docker network inspect nginx_public | grep sistema-familiar
   ```

3. **Testar conectividade:**
   ```bash
   docker exec $(docker ps -q -f name=nginx-proxy-manager) wget -O- http://sistema-familiar_frontend:80 --timeout=5
   ```

4. **Se não estiver na rede, conectar:**
   ```bash
   docker service update --network-add nginx_public sistema-familiar_frontend
   docker service update --network-add nginx_public sistema-familiar_backend
   ```

---

## 🗄️ Configuração de Banco de Dados

### Usar Banco Existente em Docker

Se o banco de dados já está rodando em Docker separado:

#### 1. Descobrir Informações do Banco

```bash
# Listar containers PostgreSQL
docker ps | grep postgres

# Ver detalhes do container do banco
docker inspect nome-container-postgres

# Descobrir a rede do banco
docker inspect nome-container-postgres | grep -A 10 "Networks"
```

#### 2. Configurar DATABASE_URL no .env

**Se o banco estiver na mesma rede Docker:**
```env
DATABASE_URL=postgresql://usuario:senha@nome-container-postgres:5432/sistema_familiar
```

**Se o banco estiver em outro servidor:**
```env
DATABASE_URL=postgresql://usuario:senha@ip-servidor:5432/sistema_familiar
```

#### 3. Configurar Rede Externa no docker-stack.yml

Edite o arquivo `docker-stack.yml`:

```yaml
networks:
  sistema-familiar-network:
    driver: overlay
    attachable: true
  # Ajuste este nome para a rede do seu banco de dados
  external_db_network:
    external: true
    name: nome-da-rede-do-banco  # Substitua pelo nome real da rede
```

**Para descobrir o nome exato da rede:**
```bash
# Listar todas as redes
docker network ls

# Ver detalhes da rede do banco
docker network inspect nome-da-rede-do-banco
```

#### 4. Alternativa: Conectar Backend à Rede do Banco

Se preferir não modificar o docker-stack.yml:

```bash
# Após fazer o deploy
docker service update --network-add nome-da-rede-do-banco sistema-familiar_backend
```

#### 5. Verificar Conexão

```bash
# Ver logs do backend
docker service logs -f sistema-familiar_backend
```

Procure por mensagens de erro de conexão com o banco. Se tudo estiver correto, você verá a aplicação iniciando normalmente.

---

## 🛠️ Comandos Úteis

### Desenvolvimento Local

```powershell
# Ver status dos serviços
.\status.ps1

# Iniciar tudo
.\start.ps1

# Parar tudo
.\stop.ps1

# Iniciar apenas backend
.\start-backend.ps1

# Iniciar apenas frontend
.\start-frontend.ps1
```

### Deploy em VPS

```bash
# Ver status dos serviços
docker stack services sistema-familiar

# Ver logs em tempo real
docker service logs -f sistema-familiar_backend
docker service logs -f sistema-familiar_frontend

# Reiniciar um serviço
docker service update --force sistema-familiar_backend
docker service update --force sistema-familiar_frontend

# Ver detalhes de um serviço
docker service ps sistema-familiar_backend

# Acessar container
docker exec -it $(docker ps -q -f name=sistema-familiar-backend) /bin/bash

# Remover o stack
docker stack rm sistema-familiar
```

### Verificar Redes

```bash
# Listar todas as redes
docker network ls

# Ver detalhes de uma rede
docker network inspect nginx_public

# Ver containers em uma rede
docker network inspect nginx_public | grep sistema-familiar
```

### Backup do Banco de Dados

```bash
# Backup
docker exec $(docker ps -q -f name=postgres) pg_dump -U postgres sistema_familiar > backup.sql

# Restore
docker exec -i $(docker ps -q -f name=postgres) psql -U postgres sistema_familiar < backup.sql
```

---

## 🐛 Troubleshooting

### Erro 502 Bad Gateway

O erro **502 Bad Gateway** significa que o Nginx Proxy Manager está recebendo a requisição, mas não consegue se comunicar com o backend.

#### Diagnóstico Rápido

```bash
# 1. Verificar se o backend está rodando
docker service ls | grep sistema-familiar
docker service ps sistema-familiar_backend
docker service logs --tail 50 sistema-familiar_backend

# 2. Verificar se o backend está na rede do NPM
docker service inspect sistema-familiar_backend | grep -A 10 "Networks"
docker service inspect sistema-familiar_backend | grep nginx_public

# 3. Testar se o backend responde localmente
curl http://localhost:8001/health
curl http://sistema-familiar_backend:8001/health

# 4. Testar do container do NPM
docker exec $(docker ps -q -f name=nginx-proxy-manager) wget -O- http://sistema-familiar_backend:8001/health --timeout=5
```

#### Soluções

**Solução 1: Backend não está rodando ou DATABASE_URL vazio**

```bash
# Ver logs para identificar o problema
docker service logs --tail 100 sistema-familiar_backend

# Se houver erro de DATABASE_URL vazio, use o redeploy-seguro.sh
cd /opt/sistema-familiar
./redeploy-seguro.sh
```

O `redeploy-seguro.sh` garante que as variáveis do `.env` sejam carregadas corretamente.

**Solução 2: Backend não está na rede do NPM**

Verificar o `docker-stack.yml`:

```yaml
backend:
  # ...
  networks:
    - sistema-familiar-network
    - db_network
    - nginx_public  # ⚠️ Deve estar aqui
```

Se não estiver, adicionar e fazer deploy:

```bash
# Opção 1: Adicionar manualmente
docker service update --network-add nginx_public sistema-familiar_backend

# Opção 2: Usar redeploy-seguro.sh (recomendado - garante tudo correto)
cd /opt/sistema-familiar
./redeploy-seguro.sh
```

**Solução 3: Configuração do NPM está errada**

1. Acesse o NPM: `http://seu-ip:81`
2. Vá em **Proxy Hosts**
3. Edite o Proxy Host da API
4. Verifique:
   - **Forward Hostname/IP:** `sistema-familiar_backend` (nome completo)
   - **Forward Port:** `8001`
5. Salve e teste novamente

**Solução 4: Reiniciar o backend**

```bash
# Forçar atualização do serviço
docker service update --force sistema-familiar_backend

# Aguardar alguns segundos
sleep 10

# Verificar se está rodando
docker service ps sistema-familiar_backend
docker service logs --tail 20 sistema-familiar_backend
```

**Solução 5: Recriar o stack completo (RECOMENDADO)**

Use o script `redeploy-seguro.sh` que faz tudo automaticamente:

```bash
cd /opt/sistema-familiar
git pull origin master
chmod +x redeploy-seguro.sh
./redeploy-seguro.sh
```

Este script:
- Remove o stack de forma segura (aguardando remoção completa)
- Carrega as variáveis do `.env` corretamente
- Faz deploy do stack com as configurações corretas
- Verifica se o backend está na rede `nginx_public`
- Verifica a saúde do backend

**Se ainda houver 502 após o redeploy:**
1. Reinicie o NPM para limpar cache:
   ```bash
   NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}')
   docker service update --force $NPM_SERVICE
   ```
2. Aguarde 15 segundos
3. Limpe o cache do navegador (Ctrl+Shift+R)
4. Tente novamente

### Backend não está acessível

```bash
# Verificar se o serviço está rodando
docker service ls | grep sistema-familiar
docker service ps sistema-familiar_backend

# Verificar se a porta está exposta
netstat -tuln | grep 8001

# Verificar logs de erro
docker service logs --tail 50 sistema-familiar_backend

# Verificar firewall
sudo ufw status | grep 8001

# Testar conexão localmente
curl http://localhost:8001/health
```

### Erro ao conectar no PostgreSQL

**Verificar:**
1. O PostgreSQL está rodando
2. As credenciais no `.env` estão corretas
3. O banco de dados foi criado
4. O firewall não está bloqueando a porta 5432
5. O backend está na mesma rede do banco

**Testar conexão:**
```bash
# Testar conexão com o banco
docker run --rm --network db_network postgres:15 psql $DATABASE_URL -c "SELECT 1"
```

### Erro de CORS no frontend

**Verificar:**
1. O backend está rodando
2. O CORS está configurado corretamente em `backend/app/main.py`
3. O `VITE_API_URL` está configurado corretamente

**Solução:** O backend já está configurado com `allow_origins=["*"]`, então não deve ter problema. Se tiver, verifique os logs do backend.

### Port já em uso

**Backend:**
```bash
# Ver qual processo está usando a porta
netstat -tulpn | grep 8001

# Parar processo específico
kill -9 <PID>
```

**Frontend:**
```bash
# Ver qual processo está usando a porta
netstat -tulpn | grep 5173

# Parar processo específico
kill -9 <PID>
```

### Serviços não iniciam

```bash
# Ver logs detalhados
docker service logs sistema-familiar_backend --tail 100
docker service ps sistema-familiar_backend --no-trunc

# Verificar recursos do servidor
docker system df
docker stats

# Verificar se há erros no código
docker service logs sistema-familiar_backend | grep -i error
```

### Mixed Content (HTTPS → HTTP)

**Problema:** Quando você acessa o site via HTTPS, mas o frontend tenta fazer requisições para HTTP, o navegador bloqueia.

**Solução:**
1. Configure o Custom Location `/api` no NPM
2. O frontend já está configurado para usar URL relativa (`/api/v1`) quando detectar HTTPS
3. Certifique-se de que o backend está na rede `nginx_public`

---

## 📁 Estrutura do Projeto

```
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
│   │   │   └── security.py              # JWT e criptografia
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
│   ├── Dockerfile
│   └── create_admin.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.tsx                # Layout principal com sidebar
│   │   ├── lib/
│   │   │   ├── api.ts                    # Cliente Axios configurado
│   │   │   └── utils.ts                  # Utilitários
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx              # Página inicial
│   │   │   ├── Login.tsx                  # Login
│   │   │   ├── Register.tsx               # Registro
│   │   │   ├── admin/
│   │   │   │   └── Users.tsx             # Administração de usuários
│   │   │   ├── healthcare/
│   │   │   │   ├── FamilyMembers.tsx
│   │   │   │   ├── Appointments.tsx
│   │   │   │   ├── Medications.tsx
│   │   │   │   └── Procedures.tsx
│   │   │   └── maintenance/
│   │   │       ├── Equipment.tsx
│   │   │       └── MaintenanceOrders.tsx
│   │   ├── services/
│   │   │   └── authService.ts             # Serviços de autenticação
│   │   ├── stores/
│   │   │   └── authStore.ts               # Zustand store para auth
│   │   ├── App.tsx                       # Rotas principais
│   │   ├── main.tsx                       # Entry point
│   │   └── index.css                      # Estilos globais + Tailwind
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-stack.yml                      # Configuração Docker Swarm
├── deploy.sh                             # Script de deploy
├── deploy.ps1                            # Script de deploy (Windows)
├── start.ps1                             # Iniciar serviços (Windows)
├── stop.ps1                              # Parar serviços (Windows)
├── status.ps1                            # Verificar status (Windows)
├── setup.ps1                              # Setup automático (Windows)
└── README.md                              # Este arquivo
```

---

## 📚 API Documentation

Após iniciar o backend, acesse a documentação interativa:

- **Swagger UI:** http://localhost:8001/api/v1/docs
- **ReDoc:** http://localhost:8001/api/v1/redoc

### Principais Endpoints

#### Autenticação
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Registro

#### Usuários
- `GET /api/v1/users/me` - Obter usuário atual
- `PUT /api/v1/users/me/profile` - Atualizar perfil
- `GET /api/v1/users` - Listar usuários (admin)
- `PUT /api/v1/users/{user_id}/password` - Atualizar senha (admin)
- `PUT /api/v1/users/{user_id}/activate` - Ativar/desativar usuário (admin)

#### Healthcare
- `GET /api/v1/healthcare/members` - Listar membros
- `POST /api/v1/healthcare/members` - Criar membro
- `GET /api/v1/healthcare/appointments` - Listar consultas
- `POST /api/v1/healthcare/appointments` - Criar consulta
- `GET /api/v1/healthcare/medications` - Listar medicamentos
- `POST /api/v1/healthcare/medications` - Criar medicamento

#### Maintenance
- `GET /api/v1/maintenance/equipment` - Listar equipamentos
- `POST /api/v1/maintenance/equipment` - Criar equipamento
- `GET /api/v1/maintenance/orders` - Listar ordens de manutenção
- `POST /api/v1/maintenance/orders` - Criar ordem
- `GET /api/v1/maintenance/dashboard/stats` - Estatísticas

---

## 🔒 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ Autenticação JWT
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ Proteção contra SQL Injection (SQLAlchemy ORM)
- ✅ Tokens expiram em 30 minutos
- ✅ Controle de acesso por roles (admin/staff)

---

## 📱 PWA (Progressive Web App)

O frontend é uma PWA, o que significa:

- ✅ Pode ser instalado como app no celular/desktop
- ✅ Funciona offline (cache de dados)
- ✅ Ícone na tela inicial
- ✅ Notificações push (futuro)

Para instalar:
1. Acesse pelo navegador mobile
2. Clique em "Adicionar à tela inicial"
3. Use como um app nativo!

---

## 📝 Licença

Este projeto é privado e de uso familiar.

---

## 👨‍💻 Autor

Desenvolvido com ❤️ para gestão familiar

---

**🎉 Pronto! Seu Gestão Familiar está configurado e funcionando!**

