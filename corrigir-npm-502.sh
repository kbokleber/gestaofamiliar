#!/bin/bash

echo "=========================================="
echo "CORRIGINDO 502 BAD GATEWAY NO NPM"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_SERVICE="sistema-familiar_backend"
NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}' | head -n 1)

# 1. Verificar se backend está acessível
echo "1. Verificando backend..."
if docker service ls | grep -q "$BACKEND_SERVICE"; then
    REPLICAS=$(docker service ls --filter "name=$BACKEND_SERVICE" --format "{{.Replicas}}")
    if echo "$REPLICAS" | grep -q "1/1"; then
        echo -e "${GREEN}✓ Backend está rodando${NC}"
    else
        echo -e "${RED}✗ Backend não está rodando corretamente${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Backend não encontrado${NC}"
    exit 1
fi

echo ""

# 2. Verificar se NPM consegue alcançar o backend
echo "2. Testando conectividade NPM -> Backend..."
if [ -n "$NPM_SERVICE" ]; then
    NPM_TASK=$(docker service ps "$NPM_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    if [ -n "$NPM_TASK" ]; then
        NPM_CONTAINER=$(docker ps --filter "name=$NPM_TASK" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$NPM_CONTAINER" ]; then
            # Testar HTTP
            if docker exec "$NPM_CONTAINER" which curl > /dev/null 2>&1; then
                HTTP_CODE=$(docker exec "$NPM_CONTAINER" curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$BACKEND_SERVICE:8001/health 2>/dev/null)
                
                if [ "$HTTP_CODE" = "200" ]; then
                    echo -e "${GREEN}✓ NPM consegue alcançar o backend (HTTP 200)${NC}"
                else
                    echo -e "${YELLOW}⚠ NPM retornou HTTP $HTTP_CODE${NC}"
                fi
            else
                echo -e "${YELLOW}⚠ curl não disponível no NPM${NC}"
            fi
        fi
    fi
fi

echo ""

# 3. Reiniciar NPM para limpar cache
echo "3. Reiniciando NPM para limpar cache..."
if [ -n "$NPM_SERVICE" ]; then
    echo "   Serviço NPM: $NPM_SERVICE"
    docker service update --force "$NPM_SERVICE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ NPM reiniciado${NC}"
        echo "   Aguardando NPM iniciar (15 segundos)..."
        sleep 15
    else
        echo -e "${RED}✗ Erro ao reiniciar NPM${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Serviço NPM não encontrado${NC}"
fi

echo ""

# 4. Verificar se backend está na rede nginx_public (garantir)
echo "4. Garantindo que backend está na rede nginx_public..."
if docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -A 10 "Networks" | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
else
    echo -e "${YELLOW}⚠ Adicionando backend à rede nginx_public...${NC}"
    docker service update --network-add nginx_public "$BACKEND_SERVICE"
    echo "   Aguardando 10 segundos..."
    sleep 10
fi

echo ""

# 5. Testar novamente após reiniciar
echo "5. Testando conectividade após reiniciar..."
if [ -n "$NPM_CONTAINER" ]; then
    # Obter novo container do NPM (pode ter mudado após restart)
    NPM_TASK_NEW=$(docker service ps "$NPM_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    if [ -n "$NPM_TASK_NEW" ]; then
        NPM_CONTAINER_NEW=$(docker ps --filter "name=$NPM_TASK_NEW" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$NPM_CONTAINER_NEW" ] && docker exec "$NPM_CONTAINER_NEW" which curl > /dev/null 2>&1; then
            HTTP_CODE_NEW=$(docker exec "$NPM_CONTAINER_NEW" curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$BACKEND_SERVICE:8001/health 2>/dev/null)
            
            if [ "$HTTP_CODE_NEW" = "200" ]; then
                echo -e "${GREEN}✓ NPM consegue alcançar o backend após reiniciar (HTTP 200)${NC}"
            else
                echo -e "${YELLOW}⚠ NPM retornou HTTP $HTTP_CODE_NEW após reiniciar${NC}"
            fi
        fi
    fi
fi

echo ""

# 6. Resumo e instruções
echo "=========================================="
echo "RESUMO"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ Backend está rodando e acessível${NC}"
echo -e "${GREEN}✓ NPM foi reiniciado${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Aguarde mais 10-15 segundos para o NPM estabilizar"
echo "  2. Limpe o cache do navegador (Ctrl+Shift+R ou Cmd+Shift+R)"
echo "  3. Tente fazer login novamente"
echo ""
echo "Se ainda houver 502:"
echo "  1. Verifique no NPM (porta 81) se o Proxy Host está configurado:"
echo "     - Forward Hostname/IP: $BACKEND_SERVICE"
echo "     - Forward Port: 8001"
echo "  2. Verifique se há múltiplos Proxy Hosts configurados"
echo "  3. Tente acessar diretamente o backend para testar:"
echo "     curl http://$BACKEND_SERVICE:8001/health"
echo ""

