# 🔒 Corrigir Erro Mixed Content (HTTPS -> HTTP)

## Problema

Quando você acessa o site via HTTPS (`https://gestaofamiliar.kbosolucoes.com.br`), mas o frontend tenta fazer requisições para HTTP (`http://89.116.186.192:8001`), o navegador bloqueia isso por segurança (Mixed Content).

**Erro no console:**
```
Mixed Content: The page at 'https://...' was loaded over HTTPS, 
but requested an insecure XMLHttpRequest endpoint 'http://...'. 
This request has been blocked.
```

## Solução

Fazer **tudo** passar pelo NPM via HTTPS usando URLs relativas.

### Passo 1: Rebuild do Frontend (sem VITE_API_URL)

O frontend foi corrigido para usar URL relativa quando detectar HTTPS. Rebuild sem passar `VITE_API_URL`:

```bash
cd /opt/sistema-familiar

# Rebuild do frontend (sem VITE_API_URL, vai usar URL relativa)
docker build -t sistema-familiar-frontend:latest ./frontend

# Atualizar o serviço
docker service update --image sistema-familiar-frontend:latest sistema-familiar_frontend
```

### Passo 2: Conectar Backend à Rede nginx_public

O backend precisa estar na rede `nginx_public` para o NPM acessá-lo:

```bash
# Atualizar o stack (já foi modificado no docker-stack.yml)
docker stack deploy -c docker-stack.yml sistema-familiar
```

### Passo 3: Descobrir IP do Backend

```bash
docker network inspect nginx_public | grep -A 5 "sistema-familiar_backend"
```

Anote o IP do backend (exemplo: `10.0.2.250`).

### Passo 4: Configurar NPM - Proxy Host Principal

1. Acesse o NPM: `http://seu-ip:81`
2. Edite o Proxy Host `gestaofamiliar.kbosolucoes.com.br`
3. Configure:
   - **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `10.0.2.249` (IP do frontend)
   - **Forward Port:** `80`
   - ✅ **Websockets Support**
4. Clique em **"Save"**

### Passo 5: Configurar NPM - Custom Location para /api

1. No mesmo Proxy Host, vá na aba **"Custom Locations"**
2. Clique em **"Add location"**
3. Preencha:
   - **Location:** `/api`
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `10.0.2.250` (IP do backend - descubra no Passo 3)
   - **Forward Port:** `8001`
   - ✅ **Websockets Support**
4. Clique em **"Save"**

### Passo 6: Verificar SSL no NPM

1. No Proxy Host, vá na aba **"SSL"**
2. Certifique-se de que há um certificado SSL configurado
3. Se não houver, adicione um certificado (Let's Encrypt ou seu próprio)

## Como Funciona Agora

```
Navegador (HTTPS)
    ↓
NPM (HTTPS -> HTTP interno)
    ↓
Frontend (10.0.2.249:80) → Requisições para /api/v1
    ↓
NPM (rota /api)
    ↓
Backend (10.0.2.250:8001)
```

O frontend faz requisições para `/api/v1` (URL relativa), que passa pelo NPM via HTTPS e é roteado para o backend.

## Testar

1. Acesse: `https://gestaofamiliar.kbosolucoes.com.br/login`
2. Abra o DevTools (F12) → Console
3. Deve aparecer: `API Base URL: /api/v1` (não mais `http://89.116.186.192:8001`)
4. Tente fazer login
5. Não deve mais aparecer erro de Mixed Content

## Se Ainda Não Funcionar

### Verificar se o backend está acessível:

```bash
# Testar do container do NPM (substitua ID pelo ID do container do NPM)
docker exec ID curl http://10.0.2.250:8001/health
```

### Verificar logs:

```bash
# Logs do frontend
docker service logs --tail 20 sistema-familiar_frontend

# Logs do backend
docker service logs --tail 20 sistema-familiar_backend

# Logs do NPM
docker logs $(docker ps -q -f name=nginx-proxy-manager) --tail 50
```

