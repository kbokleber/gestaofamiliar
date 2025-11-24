# 🚀 Guia Completo de Deploy - Sistema Familiar 2.0

Este guia passo a passo explica como fazer o deploy do Sistema Familiar em seu servidor VPS usando Docker Swarm.

## 📋 Pré-requisitos

- ✅ VPS com Docker e Docker Swarm instalados
- ✅ Acesso SSH ao servidor
- ✅ PostgreSQL rodando em Docker (rede: `db_network`)
- ✅ Nginx Proxy Manager rodando em Docker (rede: `nginx_public`)
- ✅ Domínio configurado (opcional, mas recomendado)

---

## 📝 Passo 1: Preparar o Código Localmente

### 1.1. Verificar se tudo está commitado

```powershell
# No seu computador Windows
cd C:\Projetos\SistemaFamiliar2.0
git status
```

Se houver alterações não commitadas, faça commit:

```powershell
git add .
git commit -m "Preparando para deploy"
git push
```

### 1.2. Verificar arquivos necessários

Certifique-se de que estes arquivos existem:
- ✅ `docker-stack.yml`
- ✅ `backend/Dockerfile`
- ✅ `frontend/Dockerfile`
- ✅ `.env.example`
- ✅ `deploy.sh`

---

## 📤 Passo 2: Enviar Código para o Servidor

### Opção A: Usando Git (Recomendado)

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

### Opção B: Usando SCP (Alternativa)

```powershell
# No seu computador Windows (PowerShell)
scp -r C:\Projetos\SistemaFamiliar2.0\* usuario@seu-servidor-ip:/opt/sistema-familiar/
```

---

## ⚙️ Passo 3: Configurar Variáveis de Ambiente

### 3.1. Criar arquivo .env no servidor

```bash
# No servidor
cd /opt/sistema-familiar
cp .env.example .env
nano .env  # ou use vi, vim, ou outro editor
```

### 3.2. Preencher o arquivo .env

Edite o arquivo `.env` com suas configurações:

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

**⚠️ IMPORTANTE:**
- A `DATABASE_URL` deve apontar para o container do PostgreSQL
- Se o PostgreSQL está na rede `db_network`, use o nome do serviço/container
- A `SECRET_KEY` deve ser uma string aleatória forte (use `openssl rand -hex 32`)

### 3.3. Gerar SECRET_KEY

```bash
# No servidor, gere uma chave secreta:
openssl rand -hex 32

# Copie o resultado e cole no .env como SECRET_KEY
```

---

## 🔍 Passo 4: Verificar Redes Docker

### 4.1. Verificar se as redes existem

```bash
# No servidor
docker network ls
```

Você deve ver:
- `db_network` (rede do banco de dados)
- `nginx_public` (rede do Nginx Proxy Manager)

### 4.2. Se as redes não existirem

Se alguma rede não existir, você precisa criá-las ou descobrir o nome correto:

```bash
# Ver redes do banco de dados
docker inspect nome-container-postgres | grep -A 10 "Networks"

# Ver redes do Nginx
docker inspect nome-container-nginx | grep -A 10 "Networks"

# Ou listar todas as redes
docker network ls
```

Se os nomes forem diferentes, edite o `docker-stack.yml` antes de continuar.

---

## 🏗️ Passo 5: Construir Imagens Docker

### 5.1. Dar permissão de execução ao script

```bash
cd /opt/sistema-familiar
chmod +x deploy.sh
```

### 5.2. Executar o deploy

```bash
./deploy.sh
```

O script irá:
1. ✅ Verificar se Docker Swarm está ativo
2. ✅ Construir as imagens `sistema-familiar-backend:latest` e `sistema-familiar-frontend:latest`
3. ✅ Verificar se o arquivo `.env` está configurado
4. ✅ Verificar se as redes Docker existem
5. ✅ Fazer o deploy do stack

**⏱️ Tempo estimado:** 5-10 minutos (dependendo da velocidade do servidor)

---

## 📊 Passo 6: Verificar Deploy

### 6.1. Verificar status dos serviços

```bash
# Ver serviços do stack
docker stack services sistema-familiar

# Ver detalhes dos serviços
docker service ps sistema-familiar_backend
docker service ps sistema-familiar_frontend
```

### 6.2. Verificar logs

```bash
# Logs do backend
docker service logs -f sistema-familiar_backend

# Logs do frontend
docker service logs -f sistema-familiar_frontend
```

### 6.3. Verificar se os serviços estão rodando

```bash
# Verificar se os containers estão rodando
docker ps | grep sistema-familiar
```

---

## 🌐 Passo 7: Configurar Nginx Proxy Manager

### 7.1. Acessar Nginx Proxy Manager

1. Acesse: `http://seu-servidor-ip:81`
2. Faça login no Nginx Proxy Manager

### 7.2. Configurar Proxy Host para Frontend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `seu-dominio.com` (ou IP do servidor)
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_frontend` (nome do serviço Docker)
   - **Forward Port:** `80`
   - ✅ Marque **"Websockets Support"**
3. Clique em **"Save"**

### 7.3. Configurar Proxy Host para Backend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `api.seu-dominio.com` (ou `seu-dominio.com/api`)
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_backend` (nome do serviço Docker)
   - **Forward Port:** `8001`
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

### 7.4. Configurar SSL (Opcional mas Recomendado)

1. Na configuração do Proxy Host, vá na aba **"SSL"**
2. Selecione **"Request a new SSL Certificate"**
3. Marque **"Force SSL"** e **"HTTP/2 Support"**
4. Clique em **"Save"**

---

## ✅ Passo 8: Testar Aplicação

### 8.1. Testar Frontend

Acesse: `http://seu-dominio.com` (ou `http://seu-servidor-ip`)

Você deve ver a tela de login do Sistema Familiar.

### 8.2. Testar Backend

Acesse: `http://seu-dominio.com/api/v1/docs` (ou `http://seu-servidor-ip/api/v1/docs`)

Você deve ver a documentação Swagger da API.

### 8.3. Testar Conexão com Banco

```bash
# Ver logs do backend para verificar conexão
docker service logs sistema-familiar_backend | grep -i "database\|connection\|error"
```

Se houver erros de conexão, verifique:
- ✅ A `DATABASE_URL` no `.env` está correta
- ✅ O banco está acessível na rede `db_network`
- ✅ As credenciais estão corretas

---

## 🔧 Comandos Úteis

### Ver status dos serviços

```bash
docker stack services sistema-familiar
```

### Ver logs em tempo real

```bash
# Backend
docker service logs -f sistema-familiar_backend

# Frontend
docker service logs -f sistema-familiar_frontend
```

### Reiniciar um serviço

```bash
# Reiniciar backend
docker service update --force sistema-familiar_backend

# Reiniciar frontend
docker service update --force sistema-familiar_frontend
```

### Atualizar após mudanças no código

```bash
cd /opt/sistema-familiar

# 1. Fazer pull das mudanças
git pull

# 2. Reconstruir imagens
docker build -t sistema-familiar-backend:latest ./backend
docker build -t sistema-familiar-frontend:latest ./frontend

# 3. Atualizar serviços
docker service update --image sistema-familiar-backend:latest sistema-familiar_backend
docker service update --image sistema-familiar-frontend:latest sistema-familiar_frontend
```

### Remover o stack (se necessário)

```bash
docker stack rm sistema-familiar
```

---

## 🐛 Troubleshooting

### Erro: "Network not found"

**Problema:** As redes `db_network` ou `nginx_public` não existem.

**Solução:**
```bash
# Verificar nomes das redes
docker network ls

# Se os nomes forem diferentes, edite o docker-stack.yml
nano docker-stack.yml
```

### Erro: "Cannot connect to database"

**Problema:** O backend não consegue conectar ao PostgreSQL.

**Solução:**
1. Verifique a `DATABASE_URL` no `.env`
2. Verifique se o banco está na rede `db_network`
3. Teste a conexão manualmente:
```bash
docker run --rm --network db_network postgres:15 psql -h nome-container-postgres -U postgres -d sistema_familiar_db
```

### Erro: "Service not found" no Nginx

**Problema:** O Nginx não encontra os serviços.

**Solução:**
1. Verifique se os serviços estão rodando:
```bash
docker service ls | grep sistema-familiar
```

2. Verifique se estão na rede `nginx_public`:
```bash
docker service inspect sistema-familiar_backend | grep -A 5 "Networks"
```

3. Use o nome completo do serviço no Nginx: `sistema-familiar_backend` e `sistema-familiar_frontend`

### Serviços não iniciam

**Problema:** Os serviços ficam em "pending" ou "failed".

**Solução:**
```bash
# Ver logs detalhados
docker service ps sistema-familiar_backend --no-trunc
docker service ps sistema-familiar_frontend --no-trunc

# Verificar recursos do servidor
docker system df
docker stats
```

---

## 📞 Próximos Passos

Após o deploy bem-sucedido:

1. ✅ Criar usuário administrador (se necessário):
   ```bash
   docker exec -it $(docker ps -q -f name=sistema-familiar_backend) python create_admin.py
   ```

2. ✅ Configurar domínio e SSL no Nginx Proxy Manager

3. ✅ Fazer backup regular do banco de dados

4. ✅ Configurar monitoramento (opcional)

---

## 📚 Documentação Adicional

- `README-DEPLOY.md` - Documentação técnica detalhada
- `CONFIGURAR-BANCO-EXTERNO.md` - Configuração do banco
- `CONFIGURAR-NGINX-EXTERNO.md` - Configuração do Nginx

---

**🎉 Parabéns! Seu Sistema Familiar está no ar!**

