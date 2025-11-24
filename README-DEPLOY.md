# 🚀 Guia de Deploy - Docker Swarm

Este guia explica como fazer deploy do Sistema Familiar em uma VPS usando Docker Swarm.

## 📋 Pré-requisitos

- VPS com Docker e Docker Swarm instalados
- Acesso SSH à VPS
- Domínio configurado (opcional, para produção)

## 🔧 Passo a Passo

### 0. Preparar Conexão com Banco Existente

Se o banco de dados já está rodando em Docker separado:

```bash
# Descobrir a rede do banco de dados
docker inspect nome-container-postgres | grep NetworkMode

# Ou listar todas as redes
docker network ls

# Criar rede externa (se necessário) ou usar a rede existente
# No docker-stack.yml, ajuste o nome da rede em "external_db_network"
```

### 1. Preparar a VPS

```bash
# Conectar via SSH
ssh usuario@seu-servidor

# Instalar Docker (se não estiver instalado)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Inicializar Docker Swarm
docker swarm init
```

### 2. Enviar Código para a VPS

```bash
# Na sua máquina local, enviar arquivos via SCP ou Git
scp -r . usuario@seu-servidor:/opt/sistema-familiar

# Ou usar Git
git clone seu-repositorio /opt/sistema-familiar
cd /opt/sistema-familiar
```

### 3. Configurar Variáveis de Ambiente

```bash
# Na VPS, criar arquivo .env
cd /opt/sistema-familiar
cp .env.example .env
nano .env
```

Edite o `.env` com suas configurações:

```env
# Database - URL completa de conexão com o banco existente
# Se o banco estiver na mesma rede Docker:
DATABASE_URL=postgresql://usuario:senha@nome-container-postgres:5432/sistema_familiar

# Se o banco estiver em outro servidor:
DATABASE_URL=postgresql://usuario:senha@ip-servidor:5432/sistema_familiar

# Backend
SECRET_KEY=chave-secreta-com-pelo-menos-32-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Importante:** 
- Se o banco estiver em outro container Docker, você precisa conectar o backend à mesma rede do banco
- Para descobrir a rede do banco: `docker inspect nome-container-postgres | grep NetworkMode`
- Para conectar à rede: `docker network connect nome-rede-backend nome-container-backend`
- Ou ajuste o `docker-stack.yml` para usar a rede externa correta

### 4. Build e Deploy

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**Ou manualmente:**
```bash
# Build das imagens
docker build -t sistema-familiar-backend:latest ./backend
docker build -t sistema-familiar-frontend:latest ./frontend

# Deploy do stack
docker stack deploy -c docker-stack.yml sistema-familiar
```

### 5. Verificar Status

```bash
# Ver serviços
docker stack services sistema-familiar

# Ver logs
docker service logs -f sistema-familiar_backend
docker service logs -f sistema-familiar_frontend

# Ver containers
docker stack ps sistema-familiar
```

### 6. Configurar Nginx Externo como Proxy Reverso

Se você já tem um Nginx rodando em Docker separado, veja o guia detalhado em `CONFIGURAR-NGINX-EXTERNO.md`.

Resumo rápido:
1. Descobrir a rede do Nginx: `docker network ls`
2. Ajustar `docker-stack.yml` para conectar à rede do Nginx
3. Configurar o Nginx com o arquivo `nginx-proxy-exemplo.conf`
4. Testar e verificar logs

### 6.1. Configurar Nginx/Proxy Reverso Manual (Alternativa)

Se quiser usar um domínio, configure Nginx ou Traefik:

**Nginx exemplo:**
```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔄 Atualizações

Para atualizar a aplicação:

```bash
# 1. Fazer pull das mudanças (se usar Git)
git pull

# 2. Rebuild das imagens
docker build -t sistema-familiar-backend:latest ./backend
docker build -t sistema-familiar-frontend:latest ./frontend

# 3. Atualizar o stack
docker stack deploy -c docker-stack.yml sistema-familiar

# 4. Verificar atualização
docker service update --force sistema-familiar_backend
docker service update --force sistema-familiar_frontend
```

## 🗑️ Remover Stack

```bash
docker stack rm sistema-familiar
```

## 📝 Comandos Úteis

```bash
# Ver logs em tempo real
docker service logs -f sistema-familiar_backend

# Escalar serviços
docker service scale sistema-familiar_backend=3

# Ver status detalhado
docker stack ps sistema-familiar

# Acessar container
docker exec -it $(docker ps -q -f name=sistema-familiar-backend) /bin/bash

# Backup do banco de dados
docker exec $(docker ps -q -f name=postgres) pg_dump -U postgres sistema_familiar > backup.sql
```

## 🔒 Segurança

1. **Altere todas as senhas padrão** no arquivo `.env`
2. **Use HTTPS** em produção (configure certificado SSL)
3. **Configure firewall** para permitir apenas portas necessárias
4. **Faça backups regulares** do banco de dados
5. **Mantenha Docker e imagens atualizados**

## 🐛 Troubleshooting

### Serviços não iniciam
```bash
# Ver logs detalhados
docker service logs sistema-familiar_backend --tail 100

# Verificar se há erros
docker stack ps sistema-familiar --no-trunc
```

### Banco de dados não conecta
```bash
# Verificar se postgres está rodando
docker service ps sistema-familiar_postgres

# Verificar logs do postgres
docker service logs sistema-familiar_postgres
```

### Portas já em uso
```bash
# Verificar portas em uso
netstat -tulpn | grep :8001
netstat -tulpn | grep :80

# Parar serviços conflitantes ou alterar portas no docker-stack.yml
```

## 📞 Suporte

Em caso de problemas, verifique:
1. Logs dos serviços: `docker service logs`
2. Status do stack: `docker stack services sistema-familiar`
3. Recursos da VPS: `docker stats`

