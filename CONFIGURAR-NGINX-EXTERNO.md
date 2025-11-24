# 🔄 Configurar Nginx Externo como Proxy Reverso

Este guia explica como configurar seu Nginx existente para fazer proxy reverso do Sistema Familiar.

## 📋 Pré-requisitos

- Nginx rodando em Docker separado
- Sistema Familiar deployado no Docker Swarm
- Ambos na mesma rede Docker ou redes conectadas

## 🔍 Passo 1: Descobrir Informações dos Serviços

### Descobrir nomes dos serviços no Docker Swarm

```bash
# Listar serviços do stack
docker service ls | grep sistema-familiar

# Ver detalhes do serviço frontend
docker service ps sistema-familiar_frontend

# Ver detalhes do serviço backend
docker service ps sistema-familiar_backend

# Ver IPs dos containers
docker service inspect sistema-familiar_frontend --format '{{range .Endpoint.VirtualIPs}}{{.Addr}}{{end}}'
docker service inspect sistema-familiar_backend --format '{{range .Endpoint.VirtualIPs}}{{.Addr}}{{end}}'
```

### Descobrir a rede do Nginx

```bash
# Ver qual rede o Nginx está usando
docker inspect nome-container-nginx | grep -A 10 "Networks"

# Ou listar todas as redes
docker network ls
```

## 🔧 Passo 2: Conectar Serviços à Rede do Nginx

### Opção A: Ajustar docker-stack.yml (Recomendado)

Edite o arquivo `docker-stack.yml` e ajuste o nome da rede:

```yaml
networks:
  nginx_network:
    external: true
    name: nome-real-da-rede-do-nginx  # Substitua aqui
```

Depois faça o deploy:
```bash
docker stack deploy -c docker-stack.yml sistema-familiar
```

### Opção B: Conectar após o deploy

```bash
# Conectar frontend à rede do Nginx
docker service update --network-add nome-rede-nginx sistema-familiar_frontend

# Conectar backend à rede do Nginx
docker service update --network-add nome-rede-nginx sistema-familiar_backend
```

## 📝 Passo 3: Configurar Nginx

### 3.1. Adicionar configuração ao Nginx

Copie o conteúdo do arquivo `nginx-proxy-exemplo.conf` e adicione ao seu Nginx.

**Se usar Nginx em Docker:**

```bash
# Copiar arquivo de configuração para o container do Nginx
docker cp nginx-proxy-exemplo.conf nome-container-nginx:/etc/nginx/conf.d/sistema-familiar.conf

# Ou montar como volume no docker-compose do Nginx:
# volumes:
#   - ./nginx-proxy-exemplo.conf:/etc/nginx/conf.d/sistema-familiar.conf
```

### 3.2. Ajustar nomes dos serviços

No arquivo de configuração do Nginx, ajuste os nomes dos serviços:

```nginx
upstream sistema-familiar-frontend {
    # Use o nome do serviço do Docker Swarm
    server sistema-familiar_frontend:80;
}

upstream sistema-familiar-backend {
    # Use o nome do serviço do Docker Swarm
    server sistema-familiar_backend:8001;
}
```

**Se os serviços estiverem em redes diferentes, use IPs:**

```bash
# Descobrir IP do container frontend
docker inspect $(docker ps -q -f name=sistema-familiar-frontend) | grep IPAddress

# Descobrir IP do container backend
docker inspect $(docker ps -q -f name=sistema-familiar-backend) | grep IPAddress
```

Depois use no Nginx:
```nginx
upstream sistema-familiar-frontend {
    server 172.18.0.5:80;  # IP do container frontend
}

upstream sistema-familiar-backend {
    server 172.18.0.6:8001;  # IP do container backend
}
```

### 3.3. Testar configuração do Nginx

```bash
# Testar configuração
docker exec nome-container-nginx nginx -t

# Recarregar Nginx
docker exec nome-container-nginx nginx -s reload
# Ou reiniciar o container
docker restart nome-container-nginx
```

## ✅ Passo 4: Verificar Funcionamento

### Testar Frontend
```bash
curl http://seu-dominio.com
# Deve retornar HTML do React
```

### Testar Backend
```bash
curl http://seu-dominio.com/api/v1/health
# Deve retornar resposta da API
```

### Ver logs
```bash
# Logs do Nginx
docker logs nome-container-nginx

# Logs do frontend
docker service logs -f sistema-familiar_frontend

# Logs do backend
docker service logs -f sistema-familiar_backend
```

## 🔄 Atualizações

Quando atualizar o sistema:

```bash
# 1. Rebuild e deploy
docker stack deploy -c docker-stack.yml sistema-familiar

# 2. Verificar se serviços estão rodando
docker service ls | grep sistema-familiar

# 3. Nginx continuará funcionando normalmente
# (não precisa reiniciar o Nginx)
```

## 🐛 Troubleshooting

### Erro: "upstream not found"
- Verifique se os serviços estão na mesma rede do Nginx
- Verifique se os nomes dos serviços estão corretos
- Use `docker network inspect nome-rede` para ver containers conectados

### Erro: "connection refused"
- Verifique se os serviços estão rodando: `docker service ps sistema-familiar_frontend`
- Verifique se as portas estão corretas (80 para frontend, 8001 para backend)
- Verifique firewall/iptables

### Frontend carrega mas API não funciona
- Verifique se o backend está acessível: `curl http://sistema-familiar_backend:8001/api/v1/health`
- Verifique CORS no backend (deve permitir o domínio do frontend)
- Verifique logs do backend para erros

### 502 Bad Gateway
- Verifique se os serviços estão rodando
- Verifique se estão na mesma rede
- Verifique logs do Nginx: `docker logs nome-container-nginx`

## 📚 Exemplo Completo

### Estrutura de Redes

```
Nginx Container (rede: nginx-network)
    ↓
Sistema Familiar Frontend (rede: sistema-familiar-network + nginx-network)
    ↓
Sistema Familiar Backend (rede: sistema-familiar-network + nginx-network + db-network)
    ↓
PostgreSQL (rede: db-network)
```

### docker-stack.yml ajustado

```yaml
networks:
  sistema-familiar-network:
    driver: overlay
  external_db_network:
    external: true
    name: postgres-network  # Nome real da rede do banco
  nginx_network:
    external: true
    name: nginx-network  # Nome real da rede do Nginx
```

### Nginx config

```nginx
upstream sistema-familiar-frontend {
    server sistema-familiar_frontend:80;
}

upstream sistema-familiar-backend {
    server sistema-familiar_backend:8001;
}

server {
    listen 80;
    server_name sistema-familiar.com;

    location / {
        proxy_pass http://sistema-familiar-frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api {
        proxy_pass http://sistema-familiar-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

