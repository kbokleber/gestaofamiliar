# 🔧 Solução Passo a Passo: NPM Offline

## Problema Identificado

O NPM está na rede `ingress`, mas o frontend está na rede `nginx_public`. Por isso o NPM não consegue acessar pelo nome do serviço.

## Solução: Passo a Passo

### Passo 1: Verificar se o NPM também está na rede nginx_public

```bash
docker network inspect nginx_public | grep nginx
```

**Se aparecer o NPM na lista:** Ótimo! Continue para o Passo 2.
**Se NÃO aparecer:** O NPM precisa ser conectado à rede nginx_public (veja Passo 1.5)

### Passo 1.5 (se necessário): Conectar NPM à rede nginx_public

```bash
# Ver o nome do serviço do NPM
docker service ls | grep nginx

# Conectar o serviço do NPM à rede nginx_public
# (Substitua nginx_app pelo nome real do serviço)
docker service update --network-add nginx_public nginx_app
```

### Passo 2: Testar se o NPM consegue acessar o frontend

```bash
# Testar do container do NPM
docker exec nginx_app.1.ma3d39zjb64ctrsv6vc1gztdt wget -O- http://sistema-familiar_frontend:80 --timeout=5
```

**Se funcionar:** Continue para o Passo 3.
**Se não funcionar:** Use a Solução Alternativa (Passo 4)

### Passo 3: Atualizar configuração no NPM

1. Acesse o NPM: `http://seu-ip:81`
2. Edite o Proxy Host `gestaofamiliar.kbosolucoes.com.br`
3. Verifique:
   - **Forward Hostname/IP:** `sistema-familiar_frontend`
   - **Forward Port:** `80`
4. Clique em **"Save"**
5. Aguarde alguns segundos e verifique se ficou "Online"

### Passo 4: Solução Alternativa (Usar IP)

Se o Passo 2 não funcionar, use o IP diretamente:

1. No NPM, edite o Proxy Host
2. Altere:
   - **Forward Hostname/IP:** `10.0.2.249` (IP do frontend)
   - **Forward Port:** `80`
3. Clique em **"Save"**

Isso deve funcionar imediatamente.

### Passo 5: Configurar Custom Location para /api

1. No mesmo Proxy Host, vá na aba **"Custom Locations"**
2. Clique em **"Add location"**
3. Preencha:
   - **Location:** `/api`
   - **Forward Hostname/IP:** `10.0.2.249` (ou descubra o IP do backend)
   - **Forward Port:** `8001`
4. Clique em **"Save"**

### Passo 6: Descobrir IP do backend (se necessário)

```bash
# Ver IP do backend na rede nginx_public
docker network inspect nginx_public | grep -A 5 "sistema-familiar_backend"
```

## Resumo da Configuração Final

**Proxy Host Principal:**
- Domain: `gestaofamiliar.kbosolucoes.com.br`
- Forward: `10.0.2.249:80` (ou `sistema-familiar_frontend:80` se o Passo 2 funcionou)

**Custom Location:**
- Location: `/api`
- Forward: `IP_DO_BACKEND:8001` (ou `sistema-familiar_backend:8001`)

---

**Comece pelo Passo 1 e me informe o resultado de cada passo!**

