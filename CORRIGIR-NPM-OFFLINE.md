# 🔧 Corrigir Proxy Host Offline no NPM

## Problema: Proxy Host fica "Offline"

Quando o NPM mostra "Offline", significa que ele não consegue acessar o serviço Docker.

## Verificações Necessárias

### 1. Verificar se o serviço está rodando

```bash
# Ver status dos serviços
docker service ls | grep sistema-familiar

# Ver detalhes do frontend
docker service ps sistema-familiar_frontend

# Ver logs do frontend
docker service logs --tail 20 sistema-familiar_frontend
```

### 2. Verificar se está na rede correta

```bash
# Verificar se o frontend está na rede nginx_public
docker service inspect sistema-familiar_frontend | grep -A 5 "Networks"

# Verificar a rede nginx_public
docker network inspect nginx_public | grep sistema-familiar
```

### 3. Testar conectividade do NPM para o serviço

```bash
# Testar se o NPM consegue acessar o frontend
docker exec $(docker ps -q -f name=nginx-proxy-manager) wget -O- http://sistema-familiar_frontend:80 --timeout=5
```

## Correções Comuns

### Erro 1: Nome do serviço incorreto

**No NPM, verifique:**
- **Forward Hostname/IP:** Deve ser exatamente `sistema-familiar_frontend` (sem erros de digitação)
- **Forward Port:** Deve ser `80` (porta interna do container)

### Erro 2: Serviço não está na rede do NPM

**Solução:**
```bash
# Conectar o frontend à rede do NPM
docker service update --network-add nginx_public sistema-familiar_frontend

# Verificar se funcionou
docker network inspect nginx_public | grep sistema-familiar
```

### Erro 3: Serviço não está rodando

**Solução:**
```bash
# Ver logs para identificar o problema
docker service logs sistema-familiar_frontend

# Se necessário, forçar atualização
docker service update --force sistema-familiar_frontend
```

### Erro 4: Porta incorreta

**Verificar:**
- No NPM: **Forward Port** deve ser `80` (não `5173`)
- A porta `5173` é apenas a exposição externa, internamente o container usa `80`

## Configuração Correta no NPM

### Proxy Host Principal:
- **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
- **Scheme:** `http`
- **Forward Hostname/IP:** `sistema-familiar_frontend` ⚠️ **Nome completo, sem erros**
- **Forward Port:** `80` ⚠️ **Porta interna**
- ✅ **Websockets Support**

### Custom Location (para /api):
- **Location:** `/api`
- **Scheme:** `http`
- **Forward Hostname/IP:** `sistema-familiar_backend` ⚠️ **Nome completo, sem erros**
- **Forward Port:** `8001`
- ✅ **Websockets Support**

## Teste Rápido

Após corrigir, teste:

```bash
# Do servidor, testar se o frontend responde
curl http://sistema-familiar_frontend:80

# Testar se o backend responde
curl http://sistema-familiar_backend:8001/health
```

Se esses comandos funcionarem, o NPM também deve conseguir acessar.

