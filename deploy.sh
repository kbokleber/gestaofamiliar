#!/bin/bash

# Script de deploy para Docker Swarm
# Uso: ./deploy.sh

set -e

echo "🚀 Iniciando deploy do Sistema Familiar..."

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar se está no diretório correto
if [ ! -f "docker-stack.yml" ]; then
    echo -e "${RED}❌ Erro: docker-stack.yml não encontrado!${NC}"
    echo "Execute este script na raiz do projeto."
    exit 1
fi

# Verificar se Docker Swarm está inicializado
if ! docker info | grep -q "Swarm: active"; then
    echo -e "${YELLOW}⚠️  Docker Swarm não está inicializado.${NC}"
    echo "Inicializando Docker Swarm..."
    docker swarm init
fi

# Build das imagens
echo -e "${GREEN}📦 Construindo imagens Docker...${NC}"
docker build -t sistema-familiar-backend:latest ./backend
docker build -t sistema-familiar-frontend:latest ./frontend

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Arquivo .env não encontrado!${NC}"
    echo "Copiando .env.example para .env..."
    cp .env.example .env
    echo -e "${RED}⚠️  IMPORTANTE: Edite o arquivo .env com suas configurações antes de continuar!${NC}"
    echo -e "${YELLOW}⚠️  Especialmente a DATABASE_URL para conectar ao banco existente!${NC}"
    exit 1
fi

# Verificar se DATABASE_URL está configurada
if ! grep -q "DATABASE_URL=" .env || grep -q "DATABASE_URL=postgresql://usuario:senha" .env; then
    echo -e "${RED}❌ Erro: DATABASE_URL não está configurada corretamente no .env!${NC}"
    echo "Configure a URL de conexão com seu banco de dados PostgreSQL existente."
    exit 1
fi

# Verificar se a rede externa do banco existe (se necessário)
echo -e "${GREEN}ℹ️  Certifique-se de que a rede do banco de dados está acessível.${NC}"
echo -e "${YELLOW}   Se o banco estiver em outra rede Docker, crie uma rede externa ou ajuste o docker-stack.yml${NC}"

# Carregar variáveis de ambiente
export $(cat .env | grep -v '^#' | xargs)

# Deploy do stack
echo -e "${GREEN}🚀 Fazendo deploy do stack...${NC}"
docker stack deploy -c docker-stack.yml sistema-familiar

# Aguardar serviços iniciarem
echo -e "${GREEN}⏳ Aguardando serviços iniciarem...${NC}"
sleep 10

# Verificar status
echo -e "${GREEN}📊 Status dos serviços:${NC}"
docker stack services sistema-familiar

echo -e "${GREEN}✅ Deploy concluído!${NC}"
echo ""
echo "Para verificar os logs:"
echo "  docker service logs -f sistema-familiar_backend"
echo "  docker service logs -f sistema-familiar_frontend"
echo ""
echo "Para remover o stack:"
echo "  docker stack rm sistema-familiar"

