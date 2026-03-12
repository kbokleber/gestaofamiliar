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

COMMIT_DATE=$(git show -s --format=%cs HEAD | tr '-' '.')
COMMIT_SHORT=$(git rev-parse --short HEAD)
APP_VERSION="${COMMIT_DATE}-${COMMIT_SHORT}"
APP_RELEASE_NAME="${APP_VERSION}"

echo -e "${GREEN}🏷️  Versão da release atual: ${APP_VERSION}${NC}"

# Build das imagens
echo -e "${GREEN}📦 Construindo imagens Docker...${NC}"
docker build -t sistema-familiar-backend:latest ./backend

# Build do frontend - usar URL relativa por padrão (funciona com DNS e IP)
# Se precisar de URL específica, defina VITE_API_URL antes de executar o script
# Usar --no-cache apenas se necessário (mais lento, mas garante rebuild completo)
if [ -n "$VITE_API_URL" ]; then
  echo -e "${GREEN}📦 Construindo frontend com API URL: ${VITE_API_URL}${NC}"
  docker build \
    --build-arg VITE_API_URL="${VITE_API_URL}" \
    --build-arg VITE_APP_VERSION="${APP_VERSION}" \
    -t sistema-familiar-frontend:latest ./frontend
else
  echo -e "${GREEN}📦 Construindo frontend com URL relativa (funciona com DNS e IP)${NC}"
  docker build \
    --build-arg VITE_APP_VERSION="${APP_VERSION}" \
    -t sistema-familiar-frontend:latest ./frontend
fi

# Se precisar forçar rebuild sem cache (descomente as linhas abaixo):
# docker build --no-cache -t sistema-familiar-backend:latest ./backend
# docker build --no-cache -t sistema-familiar-frontend:latest ./frontend

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
if ! grep -q "DATABASE_URL=" .env || grep -q "DATABASE_URL=postgresql://usuario:senha" .env || grep -q "DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco" .env; then
    echo -e "${RED}❌ Erro: DATABASE_URL não está configurada corretamente no .env!${NC}"
    echo "Configure a URL de conexão com seu banco de dados PostgreSQL existente."
    echo "Formato: postgresql://usuario:senha@host:porta/database"
    exit 1
fi

# Verificar se SECRET_KEY está configurada
if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=sua-chave-secreta" .env; then
    echo -e "${RED}❌ Erro: SECRET_KEY não está configurada no .env!${NC}"
    echo "Gere uma chave secreta com: openssl rand -hex 32"
    exit 1
fi

# Verificar se as redes externas existem
echo -e "${GREEN}🔍 Verificando redes Docker...${NC}"

if ! docker network ls | grep -q "db_network"; then
    echo -e "${YELLOW}⚠️  Rede 'db_network' não encontrada!${NC}"
    echo -e "${YELLOW}   Certifique-se de que o banco de dados está rodando e a rede existe.${NC}"
    echo -e "${YELLOW}   Você pode verificar com: docker network ls${NC}"
fi

if ! docker network ls | grep -q "nginx_public"; then
    echo -e "${YELLOW}⚠️  Rede 'nginx_public' não encontrada!${NC}"
    echo -e "${YELLOW}   Certifique-se de que o Nginx Proxy Manager está rodando e a rede existe.${NC}"
    echo -e "${YELLOW}   Você pode verificar com: docker network ls${NC}"
fi

# Carregar variáveis de ambiente
# Criar um arquivo temporário limpo sem comentários
# Filtrar apenas linhas válidas no formato VAR=valor
TMP_ENV=$(mktemp)
while IFS= read -r line || [ -n "$line" ]; do
    # Ignorar linhas vazias e comentários
    if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
        # Remover comentários inline
        line="${line%%#*}"
        # Remover espaços em branco no início e fim
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        # Incluir apenas linhas que contêm = e têm pelo menos um caractere antes e depois
        if [[ -n "$line" && "$line" =~ ^[^=]+=.+$ ]]; then
            echo "$line" >> "$TMP_ENV"
        fi
    fi
done < .env
set -a
source "$TMP_ENV" 2>/dev/null || true
set +a
rm -f "$TMP_ENV"

export APP_VERSION
export APP_COMMIT_SHORT="${COMMIT_SHORT}"
export APP_RELEASE_NAME

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

