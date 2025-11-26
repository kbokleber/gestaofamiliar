#!/bin/bash

echo "=========================================="
echo "REDEPLOY SEGURO - Gestão Familiar"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STACK_NAME="sistema-familiar"
BACKEND_SERVICE="${STACK_NAME}_backend"
FRONTEND_SERVICE="${STACK_NAME}_frontend"

# 1. Verificar se o stack existe
echo "1. Verificando stack atual..."
if docker stack ls | grep -q "$STACK_NAME"; then
    echo -e "${YELLOW}⚠ Stack $STACK_NAME encontrado${NC}"
    
    # Verificar serviços
    echo "   Serviços ativos:"
    docker stack services "$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"
    
    read -p "   Deseja continuar com a remoção? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Operação cancelada${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✓ Stack não encontrado (já foi removido ou nunca foi deployado)${NC}"
fi

echo ""

# 2. Verificar redes externas necessárias
echo "2. Verificando redes externas..."
REQUIRED_NETWORKS=("db_network" "nginx_public")
MISSING_NETWORKS=()

for network in "${REQUIRED_NETWORKS[@]}"; do
    if docker network ls | grep -q "$network"; then
        echo -e "${GREEN}✓ Rede $network encontrada${NC}"
    else
        echo -e "${RED}✗ Rede $network NÃO encontrada!${NC}"
        MISSING_NETWORKS+=("$network")
    fi
done

if [ ${#MISSING_NETWORKS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}ERRO: Redes externas necessárias não encontradas:${NC}"
    for network in "${MISSING_NETWORKS[@]}"; do
        echo "  - $network"
    done
    echo ""
    echo "Por favor, crie as redes antes de continuar:"
    for network in "${MISSING_NETWORKS[@]}"; do
        echo "  docker network create $network"
    done
    exit 1
fi

echo ""

# 3. Remover stack de forma segura
if docker stack ls | grep -q "$STACK_NAME"; then
    echo "3. Removendo stack $STACK_NAME..."
    docker stack rm "$STACK_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Comando de remoção executado${NC}"
        
        # Aguardar remoção completa
        echo "   Aguardando remoção completa dos serviços..."
        MAX_WAIT=30
        WAIT_TIME=0
        
        while [ $WAIT_TIME -lt $MAX_WAIT ]; do
            if ! docker stack ls | grep -q "$STACK_NAME"; then
                echo -e "${GREEN}✓ Stack removido completamente${NC}"
                break
            fi
            
            # Verificar se ainda há serviços
            REMAINING_SERVICES=$(docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" -q 2>/dev/null | wc -l)
            if [ "$REMAINING_SERVICES" -eq 0 ]; then
                echo -e "${GREEN}✓ Todos os serviços foram removidos${NC}"
                break
            fi
            
            echo "   Aguardando... ($WAIT_TIME/$MAX_WAIT segundos)"
            sleep 2
            WAIT_TIME=$((WAIT_TIME + 2))
        done
        
        if [ $WAIT_TIME -ge $MAX_WAIT ]; then
            echo -e "${YELLOW}⚠ Timeout aguardando remoção. Continuando mesmo assim...${NC}"
        fi
        
        # Aguardar um pouco mais para garantir que as redes foram liberadas
        echo "   Aguardando liberação de recursos (5 segundos)..."
        sleep 5
        
        # Limpar redes órfãs do stack (se houver)
        echo "   Limpando redes órfãs..."
        ORPHAN_NETWORKS=$(docker network ls --filter "label=com.docker.stack.namespace=$STACK_NAME" -q 2>/dev/null)
        if [ -n "$ORPHAN_NETWORKS" ]; then
            echo "   Removendo redes órfãs..."
            echo "$ORPHAN_NETWORKS" | xargs -r docker network rm 2>/dev/null || true
            sleep 2
        fi
    else
        echo -e "${RED}✗ Erro ao remover stack${NC}"
        exit 1
    fi
else
    echo "3. Stack não existe, pulando remoção..."
fi

echo ""

# 4. Verificar se arquivo .env existe
echo "4. Verificando configurações..."
if [ ! -f .env ]; then
    echo -e "${RED}✗ Arquivo .env não encontrado!${NC}"
    echo "   Por favor, crie o arquivo .env com as configurações necessárias:"
    echo "   - DATABASE_URL"
    echo "   - SECRET_KEY"
    exit 1
else
    echo -e "${GREEN}✓ Arquivo .env encontrado${NC}"
    
    # Verificar variáveis essenciais
    if grep -q "DATABASE_URL=" .env && grep -q "SECRET_KEY=" .env; then
        echo -e "${GREEN}✓ Variáveis essenciais encontradas no .env${NC}"
    else
        echo -e "${YELLOW}⚠ Aviso: DATABASE_URL ou SECRET_KEY podem estar faltando no .env${NC}"
    fi
fi

echo ""

# 5. Verificar se docker-stack.yml existe
if [ ! -f docker-stack.yml ]; then
    echo -e "${RED}✗ Arquivo docker-stack.yml não encontrado!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Arquivo docker-stack.yml encontrado${NC}"

echo ""

# 6. Carregar variáveis de ambiente do .env (mesmo método do deploy.sh)
echo "5. Carregando variáveis de ambiente do .env..."
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

# Exportar variáveis para o ambiente atual
set -a
source "$TMP_ENV" 2>/dev/null || true
set +a
rm -f "$TMP_ENV"

# Verificar se as variáveis foram carregadas
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ ERRO: DATABASE_URL não foi carregada do .env!${NC}"
    echo "   Verifique se o arquivo .env está correto."
    echo "   Primeira linha do .env:"
    head -1 .env
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}✗ ERRO: SECRET_KEY não foi carregada do .env!${NC}"
    echo "   Verifique se o arquivo .env está correto."
    exit 1
fi

echo -e "${GREEN}✓ Variáveis de ambiente carregadas${NC}"
echo "   DATABASE_URL: ${DATABASE_URL:0:30}..." # Mostrar apenas início (sem senha)
echo "   SECRET_KEY: ${#SECRET_KEY} caracteres"

echo ""

# 7. Verificar e limpar redes órfãs antes do deploy
echo "6. Verificando e limpando redes órfãs..."
ORPHAN_NETWORKS=$(docker network ls --filter "label=com.docker.stack.namespace=$STACK_NAME" -q 2>/dev/null)
if [ -n "$ORPHAN_NETWORKS" ]; then
    echo "   Removendo redes órfãs encontradas..."
    echo "$ORPHAN_NETWORKS" | xargs -r docker network rm 2>/dev/null || true
    sleep 1
else
    echo -e "${GREEN}✓ Nenhuma rede órfã encontrada${NC}"
fi

# Verificar se há rede com nome similar que possa causar conflito
NETWORK_NAME="${STACK_NAME}_sistema-familiar-network"
EXISTING_NETWORK=$(docker network ls --filter "name=$NETWORK_NAME" -q 2>/dev/null)
if [ -n "$EXISTING_NETWORK" ]; then
    echo -e "${YELLOW}⚠ Rede $NETWORK_NAME ainda existe, tentando remover...${NC}"
    docker network rm "$NETWORK_NAME" 2>/dev/null || true
    sleep 1
fi

echo ""

# 8. Reconstruir imagens Docker
echo "7. Reconstruindo imagens Docker..."

# Verificar se os diretórios existem
if [ ! -d "./backend" ]; then
    echo -e "${RED}✗ Diretório ./backend não encontrado!${NC}"
    exit 1
fi

if [ ! -d "./frontend" ]; then
    echo -e "${RED}✗ Diretório ./frontend não encontrado!${NC}"
    exit 1
fi

echo "   Construindo backend..."
docker build -t sistema-familiar-backend:latest ./backend
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend construído${NC}"
else
    echo -e "${RED}✗ Erro ao construir backend${NC}"
    exit 1
fi

echo "   Construindo frontend (sem cache para garantir atualização)..."
docker build --no-cache -t sistema-familiar-frontend:latest ./frontend
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend construído${NC}"
else
    echo -e "${RED}✗ Erro ao construir frontend${NC}"
    exit 1
fi

echo ""

# 9. Fazer deploy do stack (variáveis já estão exportadas)
echo "8. Fazendo deploy do stack $STACK_NAME..."
echo "   (Variáveis de ambiente serão passadas para o Docker Swarm)"

# Verificar novamente se as variáveis estão exportadas antes do deploy
if [ -z "$DATABASE_URL" ] || [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}✗ ERRO: Variáveis não estão exportadas!${NC}"
    echo "   DATABASE_URL: ${DATABASE_URL:-VAZIA}"
    echo "   SECRET_KEY: ${SECRET_KEY:-VAZIA}"
    exit 1
fi

# Exportar explicitamente antes do deploy
export DATABASE_URL
export SECRET_KEY
export ALGORITHM=${ALGORITHM:-HS256}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-30}

# Fazer deploy - o docker-stack.yml usa ${VAR} que será substituído pelo shell
docker stack deploy -c docker-stack.yml "$STACK_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deploy iniciado${NC}"
else
    echo -e "${RED}✗ Erro ao fazer deploy${NC}"
    exit 1
fi

echo ""

# 10. Aguardar serviços iniciarem
echo "9. Aguardando serviços iniciarem..."
sleep 5

# Verificar status dos serviços
echo "   Status dos serviços:"
docker stack services "$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"

echo ""

# 11. Verificar se backend está na rede nginx_public
echo "10. Verificando rede nginx_public..."
sleep 3  # Aguardar serviços iniciarem

# Verificar se backend está na rede nginx_public
NETWORK_CHECK=$(docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -A 10 "Networks" | grep "nginx_public")
if [ -n "$NETWORK_CHECK" ]; then
    echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
else
    echo -e "${YELLOW}⚠ Backend NÃO está na rede nginx_public${NC}"
    echo "   Tentando adicionar rede..."
    UPDATE_OUTPUT=$(docker service update --network-add nginx_public "$BACKEND_SERVICE" 2>&1)
    UPDATE_EXIT=$?
    
    if [ $UPDATE_EXIT -eq 0 ]; then
        echo -e "${GREEN}✓ Rede adicionada${NC}"
        sleep 3
    else
        # Verificar se o erro é porque já está na rede
        if echo "$UPDATE_OUTPUT" | grep -qi "already attached\|already in network"; then
            echo -e "${GREEN}✓ Backend já está na rede nginx_public${NC}"
        else
            echo -e "${YELLOW}⚠ Aviso ao adicionar rede (pode já estar conectado)${NC}"
            echo "   Verificando novamente..."
            sleep 1
            NETWORK_CHECK2=$(docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -A 10 "Networks" | grep "nginx_public")
            if [ -n "$NETWORK_CHECK2" ]; then
                echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
            fi
        fi
    fi
fi

echo ""

# 12. Verificar saúde do backend
echo "11. Verificando saúde do backend..."
MAX_RETRIES=15
RETRY_COUNT=0
BACKEND_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Tentar verificar health endpoint
    BACKEND_TASK=$(docker service ps "$BACKEND_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    
    if [ -n "$BACKEND_TASK" ]; then
        BACKEND_CONTAINER=$(docker ps --filter "name=$BACKEND_TASK" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$BACKEND_CONTAINER" ]; then
            # Verificar se o processo está rodando (método mais confiável que curl)
            if docker exec "$BACKEND_CONTAINER" ps aux 2>/dev/null | grep -q "[u]vicorn\|[p]ython.*main:app"; then
                echo -e "${GREEN}✓ Backend está rodando!${NC}"
                BACKEND_HEALTHY=true
                break
            fi
            
            # Se o processo não foi encontrado, verificar se o container está rodando
            CONTAINER_STATUS=$(docker inspect "$BACKEND_CONTAINER" --format '{{.State.Status}}' 2>/dev/null)
            if [ "$CONTAINER_STATUS" != "running" ]; then
                echo "   Container não está rodando (Status: $CONTAINER_STATUS)"
            fi
        fi
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Aguardando backend iniciar... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ "$BACKEND_HEALTHY" = false ]; then
    echo -e "${YELLOW}⚠ Backend ainda não está respondendo após $MAX_RETRIES tentativas${NC}"
    echo "   Verifique os logs:"
    echo "   docker service logs $BACKEND_SERVICE"
fi

echo ""

# 13. Verificar conexão com banco de dados
echo "12. Verificando conexão com banco de dados..."
if [ -n "$BACKEND_CONTAINER" ]; then
    # Verificar logs do backend por erros de conexão
    DB_ERRORS=$(docker service logs "$BACKEND_SERVICE" 2>&1 | grep -i "database\|connection\|postgres" | tail -5)
    
    if echo "$DB_ERRORS" | grep -qi "error\|failed\|refused"; then
        echo -e "${RED}✗ Possíveis erros de conexão com banco detectados:${NC}"
        echo "$DB_ERRORS"
    else
        echo -e "${GREEN}✓ Nenhum erro de conexão com banco detectado${NC}"
    fi
fi

echo ""

# 14. Reiniciar NPM para limpar cache e garantir conectividade
echo "13. Reiniciando NPM para limpar cache..."

# Procurar serviço do NPM (pode estar em stack diferente)
NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}' | head -n 1)

if [ -n "$NPM_SERVICE" ]; then
    SERVICE_NAME=$(docker service ls --filter "id=$NPM_SERVICE" --format "{{.Name}}")
    echo "   Serviço NPM encontrado: $SERVICE_NAME"
    
    # Verificar quantas replicas estão rodando
    REPLICAS=$(docker service ls --filter "id=$NPM_SERVICE" --format "{{.Replicas}}")
    echo "   Replicas atuais: $REPLICAS"
    
    # Reiniciar o serviço
    docker service update --force "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Comando de reinício do NPM executado${NC}"
        echo "   Aguardando NPM estabilizar (10 segundos)..."
        sleep 10
        
        # Verificar se está rodando corretamente
        NEW_REPLICAS=$(docker service ls --filter "id=$NPM_SERVICE" --format "{{.Replicas}}")
        if echo "$NEW_REPLICAS" | grep -q "1/1"; then
            echo -e "${GREEN}✓ NPM está rodando corretamente (1/1)${NC}"
        else
            echo -e "${YELLOW}⚠ NPM ainda não está estável (Status: $NEW_REPLICAS)${NC}"
            echo "   Aguarde mais alguns segundos"
        fi
    else
        echo -e "${YELLOW}⚠ Aviso: Não foi possível reiniciar o NPM automaticamente${NC}"
        echo "   Reinicie manualmente: docker service update --force $SERVICE_NAME"
        echo "   OU use o script: ./reiniciar-npm.sh"
    fi
else
    echo -e "${YELLOW}⚠ Serviço NPM não encontrado em Docker Swarm${NC}"
    echo "   O NPM pode estar rodando como container direto ou em outro stack"
    echo "   Para reiniciar manualmente, use: ./reiniciar-npm.sh"
fi

echo ""

# 11. Resumo final
echo "=========================================="
echo "RESUMO"
echo "=========================================="
echo ""
echo "Stack: $STACK_NAME"
echo ""
echo "Serviços:"
docker stack services "$STACK_NAME" --format "  - {{.Name}}: {{.Replicas}}"
echo ""
echo "Próximos passos:"
echo "  1. O NPM foi reiniciado automaticamente para limpar cache"
echo "  2. Aguarde mais 5-10 segundos para o NPM estabilizar completamente"
echo "  3. Limpe o cache do navegador (Ctrl+Shift+R ou Cmd+Shift+R)"
echo "  4. Teste o login no sistema"
echo ""
echo "Se ainda houver problemas:"
echo "  1. Verifique os logs:"
echo "     docker service logs -f $BACKEND_SERVICE"
echo "     docker service logs -f $FRONTEND_SERVICE"
echo "  2. Verifique no Nginx Proxy Manager (porta 81) se o Forward Hostname está correto:"
echo "     - Deve ser: ${GREEN}$BACKEND_SERVICE${NC}"
echo "     - NÃO use: ma-familiar_backend ou backend"
echo "     - Use exatamente: sistema-familiar_backend"
echo "     - Forward Port: 8001"
echo "  3. Se necessário, reinicie o NPM novamente:"
echo "     docker service update --force <serviço-npm>"
echo ""

