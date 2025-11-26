#!/bin/bash

echo "=========================================="
echo "VERIFICANDO SE BACKEND ESTÁ ACESSÍVEL"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_SERVICE="sistema-familiar_backend"

# 1. Verificar se o serviço está rodando
echo "1. Verificando serviço backend..."
if docker service ls | grep -q "$BACKEND_SERVICE"; then
    REPLICAS=$(docker service ls --filter "name=$BACKEND_SERVICE" --format "{{.Replicas}}")
    echo "   Status: $REPLICAS"
    
    if echo "$REPLICAS" | grep -q "1/1"; then
        echo -e "${GREEN}✓ Backend está rodando (1/1)${NC}"
    else
        echo -e "${RED}✗ Backend NÃO está rodando corretamente!${NC}"
        echo "   Verifique os logs: docker service logs -f $BACKEND_SERVICE"
        exit 1
    fi
else
    echo -e "${RED}✗ Serviço backend não encontrado!${NC}"
    exit 1
fi

echo ""

# 2. Verificar se backend está na rede nginx_public
echo "2. Verificando rede nginx_public..."
if docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -A 10 "Networks" | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
else
    echo -e "${RED}✗ Backend NÃO está na rede nginx_public!${NC}"
    echo "   Corrigindo..."
    docker service update --network-add nginx_public "$BACKEND_SERVICE"
    echo "   Aguarde 10 segundos..."
    sleep 10
fi

echo ""

# 3. Obter IP do backend na rede nginx_public
echo "3. Obtendo IP do backend na rede nginx_public..."
BACKEND_TASK=$(docker service ps "$BACKEND_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)

if [ -n "$BACKEND_TASK" ]; then
    BACKEND_CONTAINER=$(docker ps --filter "name=$BACKEND_TASK" --format "{{.ID}}" | head -n 1)
    
    if [ -n "$BACKEND_CONTAINER" ]; then
        # Obter network ID da nginx_public
        NETWORK_ID=$(docker network inspect nginx_public --format "{{.Id}}" 2>/dev/null)
        
        if [ -n "$NETWORK_ID" ]; then
            BACKEND_IP=$(docker inspect "$BACKEND_CONTAINER" --format "{{range .NetworkSettings.Networks}}{{if eq .NetworkID \"$NETWORK_ID\"}}{{.IPAddress}}{{end}}{{end}}" 2>/dev/null)
            
            if [ -n "$BACKEND_IP" ]; then
                echo -e "${GREEN}✓ IP do backend: $BACKEND_IP${NC}"
            else
                echo -e "${YELLOW}⚠ Não foi possível obter IP do backend na rede nginx_public${NC}"
            fi
        fi
    fi
fi

echo ""

# 4. Verificar se o processo está rodando no container
echo "4. Verificando processo no container..."
if [ -n "$BACKEND_CONTAINER" ]; then
    if docker exec "$BACKEND_CONTAINER" ps aux 2>/dev/null | grep -q "[u]vicorn\|[p]ython.*main:app"; then
        echo -e "${GREEN}✓ Processo Python/uvicorn está rodando${NC}"
    else
        echo -e "${RED}✗ Processo Python/uvicorn NÃO está rodando!${NC}"
        echo "   Verifique os logs: docker service logs -f $BACKEND_SERVICE"
    fi
fi

echo ""

# 5. Testar conectividade do NPM
echo "5. Testando conectividade do NPM -> Backend..."
NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}' | head -n 1)

if [ -n "$NPM_SERVICE" ]; then
    NPM_TASK=$(docker service ps "$NPM_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    if [ -n "$NPM_TASK" ]; then
        NPM_CONTAINER=$(docker ps --filter "name=$NPM_TASK" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$NPM_CONTAINER" ]; then
            echo "   Testando conexão do NPM para $BACKEND_SERVICE:8001..."
            
            # Tentar ping primeiro
            if docker exec "$NPM_CONTAINER" ping -c 1 "$BACKEND_SERVICE" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ NPM consegue fazer ping no backend${NC}"
            else
                echo -e "${RED}✗ NPM NÃO consegue fazer ping no backend${NC}"
            fi
            
            # Tentar curl se disponível
            if docker exec "$NPM_CONTAINER" which curl > /dev/null 2>&1; then
                HTTP_CODE=$(docker exec "$NPM_CONTAINER" curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$BACKEND_SERVICE:8001/health 2>/dev/null)
                
                if [ "$HTTP_CODE" = "200" ]; then
                    echo -e "${GREEN}✓ NPM consegue alcançar o backend! (HTTP 200)${NC}"
                elif [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
                    echo -e "${YELLOW}⚠ NPM alcançou o backend, mas retornou HTTP $HTTP_CODE${NC}"
                else
                    echo -e "${RED}✗ NPM NÃO consegue alcançar o backend via HTTP${NC}"
                fi
            else
                echo -e "${YELLOW}⚠ curl não disponível no NPM (ping funcionou, então a rede está OK)${NC}"
            fi
        fi
    fi
fi

echo ""

# 6. Verificar logs recentes do backend
echo "6. Últimas linhas dos logs do backend:"
docker service logs --tail 10 "$BACKEND_SERVICE" 2>&1 | tail -10

echo ""

# 7. Resumo e recomendações
echo "=========================================="
echo "RESUMO E RECOMENDAÇÕES"
echo "=========================================="
echo ""

if echo "$REPLICAS" | grep -q "1/1"; then
    echo -e "${GREEN}✓ Backend está rodando${NC}"
    
    if docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -A 10 "Networks" | grep -q "nginx_public"; then
        echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
        
        echo ""
        echo "Se ainda houver 502 Bad Gateway:"
        echo "  1. Verifique no NPM se o Forward Hostname está correto:"
        echo "     - Deve ser: $BACKEND_SERVICE"
        echo "     - NÃO use: ma-familiar_backend ou backend"
        echo "  2. Verifique a porta no NPM:"
        echo "     - Deve ser: 8001"
        echo "  3. Reinicie o NPM:"
        echo "     docker service update --force $NPM_SERVICE"
        echo "  4. Aguarde alguns segundos e teste novamente"
    else
        echo -e "${RED}✗ Backend NÃO está na rede nginx_public${NC}"
        echo "   Execute: docker service update --network-add nginx_public $BACKEND_SERVICE"
    fi
else
    echo -e "${RED}✗ Backend não está rodando corretamente${NC}"
    echo "   Verifique os logs: docker service logs -f $BACKEND_SERVICE"
fi

echo ""

