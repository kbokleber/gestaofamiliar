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
        MAX_WAIT=60
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

# 6. Carregar variáveis de ambiente do .env
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
set -a
source "$TMP_ENV" 2>/dev/null || true
set +a
rm -f "$TMP_ENV"

# Verificar se as variáveis foram carregadas
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ ERRO: DATABASE_URL não foi carregada do .env!${NC}"
    echo "   Verifique se o arquivo .env está correto."
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}✗ ERRO: SECRET_KEY não foi carregada do .env!${NC}"
    echo "   Verifique se o arquivo .env está correto."
    exit 1
fi

echo -e "${GREEN}✓ Variáveis de ambiente carregadas${NC}"

echo ""

# 7. Fazer deploy do stack
echo "6. Fazendo deploy do stack $STACK_NAME..."
docker stack deploy -c docker-stack.yml "$STACK_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deploy iniciado${NC}"
else
    echo -e "${RED}✗ Erro ao fazer deploy${NC}"
    exit 1
fi

echo ""

# 8. Aguardar serviços iniciarem
echo "7. Aguardando serviços iniciarem..."
sleep 10

# Verificar status dos serviços
echo "   Status dos serviços:"
docker stack services "$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"

echo ""

# 9. Verificar se backend está na rede nginx_public
echo "8. Verificando rede nginx_public..."
sleep 5  # Aguardar serviços iniciarem

if docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
else
    echo -e "${YELLOW}⚠ Backend NÃO está na rede nginx_public${NC}"
    echo "   Adicionando rede..."
    docker service update --network-add nginx_public "$BACKEND_SERVICE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rede adicionada${NC}"
        sleep 5
    else
        echo -e "${RED}✗ Erro ao adicionar rede${NC}"
    fi
fi

echo ""

# 10. Verificar saúde do backend
echo "9. Verificando saúde do backend..."
MAX_RETRIES=30
RETRY_COUNT=0
BACKEND_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Tentar verificar health endpoint
    BACKEND_TASK=$(docker service ps "$BACKEND_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    
    if [ -n "$BACKEND_TASK" ]; then
        BACKEND_CONTAINER=$(docker ps --filter "name=$BACKEND_TASK" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$BACKEND_CONTAINER" ]; then
            # Testar health endpoint
            HEALTH_RESPONSE=$(docker exec "$BACKEND_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null)
            
            if [ "$HEALTH_RESPONSE" = "200" ]; then
                echo -e "${GREEN}✓ Backend está respondendo! (HTTP 200)${NC}"
                BACKEND_HEALTHY=true
                break
            elif [ -n "$HEALTH_RESPONSE" ]; then
                echo "   Backend retornou HTTP $HEALTH_RESPONSE (aguardando...)"
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

# 9. Verificar conexão com banco de dados
echo "8. Verificando conexão com banco de dados..."
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

# 10. Resumo final
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
echo "  1. Aguarde alguns segundos para os serviços estabilizarem"
echo "  2. Teste o login no sistema"
echo "  3. Se houver problemas, verifique os logs:"
echo "     docker service logs -f $BACKEND_SERVICE"
echo "     docker service logs -f $FRONTEND_SERVICE"
echo ""
echo "Se o login não funcionar:"
echo "  1. Verifique se o banco de dados está acessível:"
echo "     docker network inspect db_network"
echo "  2. Verifique se o DATABASE_URL no .env está correto"
echo "  3. Verifique os logs do backend para erros específicos"
echo ""

