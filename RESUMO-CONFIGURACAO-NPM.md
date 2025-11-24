# ✅ Resumo da Configuração NPM - Funcionando

## Configuração Atual (Funcionando)

### IPs dos Serviços na Rede `nginx_public`:
- **Frontend:** `10.0.2.249:80`
- **Backend:** `10.0.2.8:8001`

### NPM - Proxy Host Principal:
- **Domain Names:** `gestaofamiliar.kbosolucoes.com.br`
- **Scheme:** `http`
- **Forward Hostname/IP:** `10.0.2.249`
- **Forward Port:** `80`
- ✅ **Websockets Support**

### NPM - Custom Location `/api`:
- **Location:** `/api`
- **Scheme:** `http`
- **Forward Hostname/IP:** `10.0.2.8`
- **Forward Port:** `8001`
- ✅ **Websockets Support**

## Como Funciona

### Acesso por IP Direto:
- URL: `http://89.116.186.192:5173`
- Frontend detecta acesso por IP e usa backend diretamente: `http://89.116.186.192:8001/api/v1`

### Acesso por DNS (HTTPS):
- URL: `https://gestaofamiliar.kbosolucoes.com.br`
- Frontend usa URL relativa: `/api/v1`
- NPM roteia:
  - `/` → Frontend (`10.0.2.249:80`)
  - `/api` → Backend (`10.0.2.8:8001`)

## Comandos Úteis

### Ver IPs dos Serviços:
```bash
# Frontend
docker network inspect nginx_public | grep -A 5 "sistema-familiar_frontend"

# Backend
docker network inspect nginx_public | grep -A 5 "sistema-familiar_backend"
```

### Verificar se Serviços Estão na Rede:
```bash
docker network inspect nginx_public | grep nginx
```

### Rebuild e Deploy:
```bash
cd /opt/sistema-familiar
git pull origin master
docker build -t sistema-familiar-frontend:latest ./frontend
docker build -t sistema-familiar-backend:latest ./backend
docker stack deploy -c docker-stack.yml sistema-familiar
```

### Atualizar Apenas Frontend:
```bash
docker build -t sistema-familiar-frontend:latest ./frontend
docker service update --image sistema-familiar-frontend:latest sistema-familiar_frontend
```

### Atualizar Apenas Backend:
```bash
docker build -t sistema-familiar-backend:latest ./backend
docker service update --image sistema-familiar-backend:latest sistema-familiar_backend
```

## Troubleshooting

### Se o NPM mostrar "Offline":
1. Verificar se os IPs ainda estão corretos (podem mudar após redeploy)
2. Testar conectividade: `curl http://10.0.2.249:80` e `curl http://10.0.2.8:8001/health`
3. Verificar se os serviços estão rodando: `docker service ps sistema-familiar_frontend sistema-familiar_backend`

### Se der erro de Mixed Content:
- Verificar se está acessando via HTTPS
- Verificar se o Custom Location `/api` está configurado corretamente
- Verificar logs do frontend: `docker service logs --tail 30 sistema-familiar_frontend`

### Se o acesso por IP parar de funcionar:
- Verificar se o backend está acessível: `curl http://89.116.186.192:8001/health`
- Verificar logs: `docker service logs --tail 30 sistema-familiar_backend`

## Arquivos Importantes

- `docker-stack.yml` - Configuração do Docker Swarm
- `frontend/src/lib/api.ts` - Lógica de detecção de URL da API
- `deploy.sh` - Script de deploy

---

**Última atualização:** Configuração funcionando com acesso por IP e DNS ✅

