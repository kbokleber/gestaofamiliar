# 🔧 Troubleshooting: Backend não está acessível

## Verificar se o serviço está rodando

```bash
# Ver status dos serviços
docker service ls | grep sistema-familiar

# Ver detalhes do serviço backend
docker service ps sistema-familiar_backend

# Ver logs do backend
docker service logs sistema-familiar_backend
```

## Verificar se a porta está exposta

```bash
# Ver se a porta 8001 está sendo usada
netstat -tuln | grep 8001
# ou
ss -tuln | grep 8001

# Ver portas expostas pelo Docker Swarm
docker service inspect sistema-familiar_backend --format '{{json .Endpoint.Ports}}' | jq
```

## Verificar se o container está rodando

```bash
# Ver containers do backend
docker ps | grep sistema-familiar-backend

# Ver todos os containers (incluindo parados)
docker ps -a | grep sistema-familiar-backend
```

## Verificar logs de erro

```bash
# Ver logs recentes do backend
docker service logs --tail 50 sistema-familiar_backend

# Ver logs em tempo real
docker service logs -f sistema-familiar_backend
```

## Verificar firewall

```bash
# Ubuntu/Debian - Verificar se a porta está aberta
sudo ufw status | grep 8001

# Se não estiver aberta, abrir:
sudo ufw allow 8001/tcp

# CentOS/RHEL
sudo firewall-cmd --list-ports | grep 8001

# Se não estiver aberta, abrir:
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

## Verificar se o backend está escutando

```bash
# Dentro do container do backend
docker exec $(docker ps -q -f name=sistema-familiar-backend) netstat -tuln | grep 8001

# Ou testar diretamente no container
docker exec $(docker ps -q -f name=sistema-familiar-backend) curl http://localhost:8001/health
```

## Verificar configuração do docker-stack.yml

```bash
# Ver se a porta está configurada corretamente
cat docker-stack.yml | grep -A 2 "ports:"
```

## Reiniciar o serviço

```bash
# Forçar atualização do serviço
docker service update --force sistema-familiar_backend

# Ou remover e recriar o stack
docker stack rm sistema-familiar
# Aguardar alguns segundos
docker stack deploy -c docker-stack.yml sistema-familiar
```

## Testar conexão localmente no servidor

```bash
# Testar se o backend responde localmente
curl http://localhost:8001/health

# Testar com o IP do servidor
curl http://89.116.186.192:8001/health

# Testar endpoint raiz
curl http://localhost:8001/
```

## Verificar variáveis de ambiente

```bash
# Ver variáveis de ambiente do serviço
docker service inspect sistema-familiar_backend --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}' | jq

# Verificar se DATABASE_URL está configurada
docker service inspect sistema-familiar_backend | grep DATABASE_URL
```

## Verificar conectividade com o banco

```bash
# Testar conexão com o banco (se o backend estiver rodando)
docker exec $(docker ps -q -f name=sistema-familiar-backend) python -c "from app.db.base import engine; print(engine.connect())"
```

## Problemas comuns e soluções

### 1. Serviço em estado "pending" ou "failed"

**Causa:** Problema ao iniciar o container (erro no código, variáveis de ambiente, etc.)

**Solução:**
```bash
# Ver logs detalhados
docker service logs sistema-familiar_backend

# Verificar se a imagem existe
docker images | grep sistema-familiar-backend

# Reconstruir a imagem se necessário
docker build -t sistema-familiar-backend:latest ./backend
```

### 2. Porta não está acessível externamente

**Causa:** Firewall bloqueando ou porta não exposta corretamente

**Solução:**
```bash
# Verificar se a porta está no docker-stack.yml
grep -A 1 "ports:" docker-stack.yml

# Verificar firewall
sudo ufw status
```

### 3. Backend não consegue conectar ao banco

**Causa:** DATABASE_URL incorreta ou banco não acessível

**Solução:**
```bash
# Verificar DATABASE_URL no .env
grep DATABASE_URL .env

# Testar conexão com o banco
docker run --rm --network db_network postgres:15 psql $DATABASE_URL -c "SELECT 1"
```

### 4. Erro de permissão

**Causa:** Problemas com permissões de arquivo ou rede

**Solução:**
```bash
# Verificar permissões
ls -la docker-stack.yml

# Verificar se está no Docker Swarm
docker info | grep Swarm
```

## Comandos úteis de diagnóstico

```bash
# Ver resumo completo do serviço
docker service inspect sistema-familiar_backend

# Ver eventos do serviço
docker service ps sistema-familiar_backend --no-trunc

# Ver uso de recursos
docker stats $(docker ps -q -f name=sistema-familiar-backend)

# Ver rede do serviço
docker network inspect sistema-familiar-network
```

## Se nada funcionar

1. **Remover o stack completamente:**
   ```bash
   docker stack rm sistema-familiar
   ```

2. **Aguardar alguns segundos**

3. **Verificar se tudo foi removido:**
   ```bash
   docker service ls | grep sistema-familiar
   docker ps | grep sistema-familiar
   ```

4. **Fazer deploy novamente:**
   ```bash
   ./deploy.sh
   ```

5. **Aguardar alguns segundos e verificar:**
   ```bash
   docker service ls
   docker service ps sistema-familiar_backend
   docker service logs sistema-familiar_backend
   ```

