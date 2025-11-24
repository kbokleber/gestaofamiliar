# 🌐 Acessar Sistema Familiar via IP (sem DNS)

Este guia explica como configurar o Nginx Proxy Manager para acessar a aplicação usando apenas o IP do servidor, sem precisar de DNS.

## 📋 Pré-requisitos

- Nginx Proxy Manager rodando e acessível
- Sistema Familiar deployado no Docker Swarm
- IP do servidor

## 🔧 Passo 1: Descobrir o IP do Servidor

```bash
# Ver IP do servidor
hostname -I
# ou
ip addr show | grep "inet " | grep -v 127.0.0.1
```

Anote o IP (exemplo: `192.168.1.100` ou `45.123.45.67`)

## 🌐 Passo 2: Configurar Nginx Proxy Manager

### 2.1. Acessar Nginx Proxy Manager

1. Acesse: `http://SEU-IP:81` (porta padrão do NPM)
2. Faça login no Nginx Proxy Manager

### 2.2. Configurar Proxy Host para Frontend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `SEU-IP` (exemplo: `192.168.1.100` ou `45.123.45.67`)
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `sistema-familiar_frontend` (nome do serviço Docker)
   - **Forward Port:** `80`
   - ✅ Marque **"Websockets Support"**
   - ✅ Marque **"Block Common Exploits"** (opcional, mas recomendado)
3. Clique em **"Save"**

### 2.3. Configurar Proxy Host para Backend

1. Clique em **"Proxy Hosts"** → **"Add Proxy Host"**
2. Preencha:
   - **Domain Names:** `SEU-IP` (mesmo IP do frontend)
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
    
    # CORS (se necessário)
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
}
```

4. Clique em **"Save"**

## ⚠️ Importante: Configurar Frontend para Aceitar IP

O frontend precisa estar configurado para aceitar requisições via IP. Verifique se o `VITE_API_URL` está configurado corretamente.

### Opção 1: Usar URL Relativa (Recomendado)

No arquivo `.env` do frontend (ou variável de ambiente), configure:

```env
VITE_API_URL=/api/v1
```

Isso faz com que o frontend use a mesma URL base para fazer requisições à API.

### Opção 2: Usar IP Direto

Se preferir, pode configurar:

```env
VITE_API_URL=http://SEU-IP/api/v1
```

Mas isso é menos flexível se você mudar o IP depois.

## ✅ Passo 3: Testar Acesso

### 3.1. Testar Frontend

Abra no navegador:
```
http://SEU-IP
```

Exemplo: `http://192.168.1.100` ou `http://45.123.45.67`

### 3.2. Testar Backend

Teste a API diretamente:
```bash
curl http://SEU-IP/api/v1/health
```

Ou no navegador:
```
http://SEU-IP/api/v1/health
```

## 🔍 Passo 4: Verificar se Está Funcionando

### Verificar serviços Docker

```bash
# Ver se os serviços estão rodando
docker service ls | grep sistema-familiar

# Ver logs do backend
docker service logs -f sistema-familiar_backend

# Ver logs do frontend
docker service logs -f sistema-familiar_frontend
```

### Verificar conectividade na rede

```bash
# Verificar se os serviços estão na rede nginx_public
docker service inspect sistema-familiar_frontend | grep -A 5 "Networks"
docker service inspect sistema-familiar_backend | grep -A 5 "Networks"
```

## 🐛 Troubleshooting

### Erro: "502 Bad Gateway"

**Problema:** O Nginx não consegue conectar aos serviços Docker.

**Solução:**
1. Verifique se os serviços estão rodando:
   ```bash
   docker service ls | grep sistema-familiar
   ```

2. Verifique se estão na rede `nginx_public`:
   ```bash
   docker network inspect nginx_public | grep sistema-familiar
   ```

3. Verifique os logs do Nginx Proxy Manager:
   - Acesse o NPM e veja os logs em "Logs" → "Access Logs"

### Erro: "Connection Refused"

**Problema:** Os serviços não estão escutando nas portas corretas.

**Solução:**
1. Verifique se o backend está na porta 8001:
   ```bash
   docker service logs sistema-familiar_backend | grep "Uvicorn running"
   ```

2. Verifique se o frontend está na porta 80:
   ```bash
   docker service logs sistema-familiar_frontend | grep "nginx"
   ```

### Erro: CORS no Frontend

**Problema:** O frontend não consegue fazer requisições à API.

**Solução:**
1. Verifique se o `VITE_API_URL` está configurado como `/api/v1` (URL relativa)
2. Verifique se o backend está configurado para aceitar CORS (já está no código)
3. Verifique os logs do backend para ver se as requisições estão chegando

### Não consigo acessar via IP

**Problema:** O Nginx Proxy Manager pode estar configurado para aceitar apenas domínios.

**Solução:**
1. No NPM, edite o Proxy Host do frontend
2. Certifique-se de que o campo "Domain Names" contém apenas o IP (sem `http://`)
3. Salve novamente

## 📝 Notas Importantes

1. **HTTPS:** Para usar HTTPS com IP, você precisará de um certificado IP ou usar um serviço como Let's Encrypt com validação por DNS (não funciona com IP direto).

2. **Firewall:** Certifique-se de que as portas 80 e 443 estão abertas no firewall do servidor:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   
   # CentOS/RHEL
   sudo firewall-cmd --permanent --add-service=http
   sudo firewall-cmd --permanent --add-service=https
   sudo firewall-cmd --reload
   ```

3. **DNS Local (Opcional):** Se quiser usar um nome ao invés de IP, pode adicionar no arquivo `/etc/hosts` do seu computador:
   ```
   SEU-IP sistema-familiar.local
   ```
   Depois acesse: `http://sistema-familiar.local`

## 🎯 Resumo Rápido

1. ✅ Descobrir IP do servidor
2. ✅ Acessar Nginx Proxy Manager em `http://SEU-IP:81`
3. ✅ Criar Proxy Host para Frontend: `SEU-IP` → `sistema-familiar_frontend:80`
4. ✅ Criar Proxy Host para Backend: `SEU-IP` → `sistema-familiar_backend:8001` com location `/api`
5. ✅ Acessar aplicação em `http://SEU-IP`

---

**Pronto!** Agora você pode acessar a aplicação usando apenas o IP do servidor. 🚀

