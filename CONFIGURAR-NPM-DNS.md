# 🌐 Configurar Nginx Proxy Manager com DNS

Este guia explica como configurar o Nginx Proxy Manager para acessar o Sistema Familiar usando um DNS (ex: `gestaofamiliar.kbosolucoes.com.br`).

## ⚠️ Problema Comum

Se você configurar:
- **Forward Hostname/IP:** `frontend`
- **Forward Port:** `5173`

Isso **NÃO vai funcionar** porque:
1. O nome do serviço no Docker Swarm é `sistema-familiar_frontend` (não apenas `frontend`)
2. A porta interna do container é `80`, não `5173` (a porta 5173 é apenas a exposição externa)

## ✅ Configuração Correta

### Passo 1: Verificar se os serviços estão na rede do NPM

Primeiro, você precisa garantir que os serviços do Sistema Familiar estão na mesma rede do Nginx Proxy Manager.

**No servidor, execute:**

```bash
# Ver qual rede o NPM está usando
docker network ls | grep nginx

# Verificar se os serviços estão nessa rede
docker service inspect sistema-familiar_frontend | grep -A 5 "Networks"
docker service inspect sistema-familiar_backend | grep -A 5 "Networks"
```

**Se os serviços NÃO estiverem na rede do NPM, você precisa:**

1. Descobrir o nome exato da rede do NPM:
   ```bash
   docker network ls
   # Procure por algo como: nginx_public, nginx-proxy-manager_default, etc.
   ```

2. Atualizar o `docker-stack.yml` para incluir essa rede (ou conectar os serviços manualmente)

### Passo 2: Configurar Proxy Host para Frontend

1. Acesse o Nginx Proxy Manager: `http://seu-ip:81`
2. Clique em **"Proxy Hosts"** → **"Add Proxy Host"** (ou edite o existente)
3. Preencha:
   - **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
   - **Scheme:** `http` (ou `https` se tiver SSL)
   - **Forward Hostname/IP:** `sistema-familiar_frontend` ⚠️ **Nome completo do serviço**
   - **Forward Port:** `80` ⚠️ **Porta interna do container, não 5173**
   - ✅ Marque **"Websockets Support"**
   - ✅ Marque **"Block Common Exploits"** (recomendado)
4. Clique em **"Save"**

### Passo 3: Configurar Proxy Host para Backend

Você tem duas opções:

#### Opção A: Subdomínio separado (Recomendado)

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `api.gestaofamiliar.kbosolucoes.com.br`
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_backend`
   - **Forward Port:** `8001`
   - ✅ Marque **"Websockets Support"**
3. Clique em **"Save"**

#### Opção B: Mesmo domínio com path `/api`

1. Edite o Proxy Host do frontend
2. Vá na aba **"Custom Locations"**
3. Clique em **"Add Location"**
4. Preencha:
   - **Location:** `/api`
   - **Forward Hostname/IP:** `sistema-familiar_backend`
   - **Forward Port:** `8001`
   - ✅ Marque **"Websockets Support"**
5. Clique em **"Save"**

### Passo 4: Configurar Frontend para usar o DNS

O frontend precisa saber qual URL usar para acessar a API. Você tem duas opções:

#### Opção 1: Usar URL relativa (Recomendado se usar Opção B acima)

Se você configurou o backend no mesmo domínio com `/api`, o frontend já está configurado para usar `/api/v1` (URL relativa).

#### Opção 2: Rebuildar frontend com URL completa

Se você usou subdomínio separado (`api.gestaofamiliar.kbosolucoes.com.br`), precisa rebuildar o frontend:

**No servidor:**

```bash
cd /opt/sistema-familiar

# Rebuildar frontend com URL da API
docker build --build-arg VITE_API_URL=http://api.gestaofamiliar.kbosolucoes.com.br/api/v1 -t sistema-familiar-frontend:latest ./frontend

# Atualizar serviço
docker service update --image sistema-familiar-frontend:latest sistema-familiar_frontend
```

## 🔍 Verificar se está funcionando

### Testar Frontend

```bash
curl http://gestaofamiliar.kbosolucoes.com.br
# Deve retornar HTML do React
```

### Testar Backend

**Se usou subdomínio:**
```bash
curl http://api.gestaofamiliar.kbosolucoes.com.br/api/v1/health
```

**Se usou path `/api`:**
```bash
curl http://gestaofamiliar.kbosolucoes.com.br/api/v1/health
```

## 🐛 Troubleshooting

### Erro: "Bad Gateway" ou "502"

**Causa:** NPM não consegue acessar o serviço Docker.

**Solução:**
1. Verificar se os serviços estão na mesma rede:
   ```bash
   docker network inspect nome-rede-npm | grep sistema-familiar
   ```

2. Se não estiverem, conectar os serviços à rede do NPM:
   ```bash
   # Descobrir nome da rede do NPM
   docker network ls | grep nginx
   
   # Conectar serviços (substitua nginx_public pelo nome real)
   docker service update --network-add nginx_public sistema-familiar_frontend
   docker service update --network-add nginx_public sistema-familiar_backend
   ```

### Erro: "Connection Refused"

**Causa:** Nome do serviço ou porta incorretos.

**Solução:**
- Verificar nome exato do serviço:
  ```bash
  docker service ls | grep sistema-familiar
  ```
- Usar sempre: `sistema-familiar_frontend` e `sistema-familiar_backend`
- Usar porta interna: `80` para frontend, `8001` para backend

### Erro: CORS no Frontend

**Causa:** Backend não está configurado para aceitar requisições do novo domínio.

**Solução:** O backend já está configurado com `allow_origins=["*"]`, então não deve ter problema. Se tiver, verifique os logs do backend.

## 📝 Resumo da Configuração Correta

**Frontend:**
- Domain: `gestaofamiliar.kbosolucoes.com.br`
- Forward: `sistema-familiar_frontend:80`

**Backend (Opção A - Subdomínio):**
- Domain: `api.gestaofamiliar.kbosolucoes.com.br`
- Forward: `sistema-familiar_backend:8001`

**Backend (Opção B - Path):**
- Domain: `gestaofamiliar.kbosolucoes.com.br`
- Custom Location: `/api` → `sistema-familiar_backend:8001`

---

**Importante:** Sempre use o nome completo do serviço (`sistema-familiar_frontend`) e a porta interna do container (`80`), não a porta exposta externamente (`5173`).

