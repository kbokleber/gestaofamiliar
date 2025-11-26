#!/bin/bash

echo "=========================================="
echo "REINICIANDO NPM"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Listar todos os serviços do NPM
echo "1. Procurando serviços do NPM..."
NPM_SERVICES=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}')

if [ -z "$NPM_SERVICES" ]; then
    echo -e "${YELLOW}⚠ Nenhum serviço do NPM encontrado em Docker Swarm${NC}"
    echo "   Verificando containers diretamente..."
    
    NPM_CONTAINERS=$(docker ps | grep nginx-proxy-manager | awk '{print $1}')
    if [ -n "$NPM_CONTAINERS" ]; then
        echo -e "${YELLOW}⚠ NPM está rodando como container, não como serviço${NC}"
        echo "   Containers encontrados:"
        docker ps | grep nginx-proxy-manager
        
        echo ""
        echo "Para reiniciar containers diretamente:"
        for container in $NPM_CONTAINERS; do
            echo "   docker restart $container"
        done
        exit 0
    else
        echo -e "${RED}✗ NPM não encontrado${NC}"
        exit 1
    fi
fi

echo "   Serviços encontrados:"
echo "$NPM_SERVICES" | while read service_id; do
    service_name=$(docker service ls --filter "id=$service_id" --format "{{.Name}}")
    replicas=$(docker service ls --filter "id=$service_id" --format "{{.Replicas}}")
    echo "   - $service_name (ID: $service_id) - Replicas: $replicas"
done

echo ""

# 2. Verificar tasks/containers do NPM
echo "2. Verificando containers do NPM..."
NPM_TASKS=$(docker service ps $(echo "$NPM_SERVICES" | head -n 1) --format "{{.Name}}" --filter "desired-state=running" 2>/dev/null)

if [ -n "$NPM_TASKS" ]; then
    echo "   Tasks rodando:"
    echo "$NPM_TASKS" | while read task; do
        container=$(docker ps --filter "name=$task" --format "{{.ID}} {{.Names}}")
        if [ -n "$container" ]; then
            echo "   - $container"
        fi
    done
fi

echo ""

# 3. Reiniciar o serviço principal do NPM
echo "3. Reiniciando serviço do NPM..."
PRIMARY_SERVICE=$(echo "$NPM_SERVICES" | head -n 1)

if [ -n "$PRIMARY_SERVICE" ]; then
    SERVICE_NAME=$(docker service ls --filter "id=$PRIMARY_SERVICE" --format "{{.Name}}")
    echo "   Serviço: $SERVICE_NAME"
    
    docker service update --force "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ NPM reiniciado${NC}"
        echo "   Aguardando NPM estabilizar (15 segundos)..."
        sleep 15
        
        # Verificar se está rodando
        NEW_REPLICAS=$(docker service ls --filter "id=$PRIMARY_SERVICE" --format "{{.Replicas}}")
        if echo "$NEW_REPLICAS" | grep -q "1/1"; then
            echo -e "${GREEN}✓ NPM está rodando corretamente (1/1)${NC}"
        else
            echo -e "${YELLOW}⚠ NPM ainda não está estável (Status: $NEW_REPLICAS)${NC}"
        fi
    else
        echo -e "${RED}✗ Erro ao reiniciar NPM${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Não foi possível identificar o serviço do NPM${NC}"
    exit 1
fi

echo ""

# 4. Verificar containers após reiniciar
echo "4. Containers do NPM após reiniciar:"
docker ps | grep nginx-proxy-manager | awk '{print "   - " $1 " (" $2 ") - " $6}'

echo ""

# 5. Resumo
echo "=========================================="
echo "RESUMO"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ NPM foi reiniciado${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Aguarde mais 5-10 segundos"
echo "  2. Limpe o cache do navegador (Ctrl+Shift+R)"
echo "  3. Tente fazer login novamente"
echo ""

