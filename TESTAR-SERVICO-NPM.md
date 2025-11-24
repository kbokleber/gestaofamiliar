# ✅ Testar se o Serviço está Acessível

## O serviço está na rede correta! ✅

O frontend está na rede `nginx_public` com IP `10.0.2.249`. Agora vamos testar se está respondendo.

## Testes no Servidor

### 1. Testar se o frontend responde diretamente:
```bash
# Testar pelo nome do serviço
curl http://sistema-familiar_frontend:80

# Testar pelo IP
curl http://10.0.2.249:80
```

### 2. Testar do container do NPM:
```bash
# Testar conectividade
docker exec $(docker ps -q -f name=nginx-proxy-manager) ping -c 2 sistema-familiar_frontend

# Testar HTTP
docker exec $(docker ps -q -f name=nginx-proxy-manager) wget -O- http://sistema-familiar_frontend:80 --timeout=5
```

### 3. Verificar logs do frontend:
```bash
docker service logs --tail 30 sistema-familiar_frontend
```

## Se os testes funcionarem mas o NPM ainda mostra "Offline"

### Solução 1: Recarregar o Proxy Host no NPM

1. No NPM, edite o Proxy Host
2. Não mude nada, apenas clique em **"Save"** novamente
3. Isso força o NPM a verificar novamente

### Solução 2: Verificar configuração no NPM

Certifique-se de que está exatamente assim:

**Proxy Host Principal:**
- **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
- **Scheme:** `http`
- **Forward Hostname/IP:** `sistema-familiar_frontend` (nome completo, sem erros)
- **Forward Port:** `80` (não 5173)
- ✅ **Websockets Support**

### Solução 3: Verificar se o container está realmente rodando

```bash
# Ver containers do frontend
docker ps | grep sistema-familiar-frontend

# Ver status do serviço
docker service ps sistema-familiar_frontend
```

### Solução 4: Reiniciar o serviço

```bash
# Forçar atualização do serviço
docker service update --force sistema-familiar_frontend

# Aguardar alguns segundos
sleep 10

# Verificar novamente
docker service ps sistema-familiar_frontend
```

## Verificar logs do NPM

Se ainda não funcionar, verifique os logs do NPM:

```bash
# Ver logs do NPM
docker logs $(docker ps -q -f name=nginx-proxy-manager) --tail 50
```

Procure por erros relacionados a `sistema-familiar_frontend` ou `gestaofamiliar.kbosolucoes.com.br`.

