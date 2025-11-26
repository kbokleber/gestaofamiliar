#!/bin/bash

echo "=========================================="
echo "DIAGNÓSTICO RÁPIDO - 502 Bad Gateway"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STACK_NAME="sistema-familiar"
BACKEND_SERVICE="${STACK_NAME}_backend"
FRONTEND_SERVICE="${STACK_NAME}_frontend"

# 1. Verificar se o stack está rodando
echo "1. Verificando stack..."
if docker stack ls | grep -q "$STACK_NAME"; then
    echo -e "${GREEN}✓ Stack $STACK_NAME está rodando${NC}"
else
    echo -e "${RED}✗ Stack $STACK_NAME NÃO está rodando!${NC}"
    echo "   Execute: ./deploy.sh ou ./redeploy-seguro.sh"
    exit 1
fi

echo ""

# 2. Verificar serviços
echo "2. Verificando serviços..."
docker stack services "$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"

BACKEND_REPLICAS=$(docker service ls --filter "name=$BACKEND_SERVICE" --format "{{.Replicas}}")
if echo "$BACKEND_REPLICAS" | grep -q "1/1"; then
    echo -e "${GREEN}✓ Backend está rodando (1/1)${NC}"
else
    echo -e "${RED}✗ Backend NÃO está rodando corretamente!${NC}"
    echo "   Status: $BACKEND_REPLICAS"
    echo "   Verifique: docker service ps $BACKEND_SERVICE"
fi

echo ""

# 3. Verificar logs do backend (últimas 20 linhas)
echo "3. Últimas linhas dos logs do backend:"
docker service logs --tail 20 "$BACKEND_SERVICE" 2>&1 | tail -20

echo ""

# 4. Verificar se backend está na rede nginx_public
echo "4. Verificando rede nginx_public..."
if docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
else
    echo -e "${RED}✗ Backend NÃO está na rede nginx_public!${NC}"
    echo "   Corrigindo..."
    docker service update --network-add nginx_public "$BACKEND_SERVICE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rede adicionada. Aguarde alguns segundos...${NC}"
        sleep 5
    else
        echo -e "${RED}✗ Erro ao adicionar rede${NC}"
    fi
fi

echo ""

# 5. Verificar se backend está respondendo localmente
echo "5. Testando backend localmente..."
BACKEND_TASK=$(docker service ps "$BACKEND_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)

if [ -n "$BACKEND_TASK" ]; then
    BACKEND_CONTAINER=$(docker ps --filter "name=$BACKEND_TASK" --format "{{.ID}}" | head -n 1)
    
        if [ -n "$BACKEND_CONTAINER" ]; then
            echo "   Container: $BACKEND_CONTAINER"
            
            # Verificar se o container está rodando
            CONTAINER_STATUS=$(docker inspect "$BACKEND_CONTAINER" --format '{{.State.Status}}' 2>/dev/null)
            if [ "$CONTAINER_STATUS" = "running" ]; then
                echo -e "${GREEN}✓ Container está rodando${NC}"
                
                # Tentar testar health endpoint (curl pode não estar disponível)
                if docker exec "$BACKEND_CONTAINER" which curl > /dev/null 2>&1; then
                    HEALTH_RESPONSE=$(docker exec "$BACKEND_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null)
                    if [ "$HEALTH_RESPONSE" = "200" ]; then
                        echo -e "${GREEN}✓ Backend está respondendo (HTTP 200)${NC}"
                    else
                        echo -e "${YELLOW}⚠ Backend retornou HTTP $HEALTH_RESPONSE${NC}"
                    fi
                else
                    echo -e "${YELLOW}⚠ curl não disponível no container (normal)${NC}"
                    echo "   Verificando se o processo Python está rodando..."
                    if docker exec "$BACKEND_CONTAINER" ps aux | grep -q "[u]vicorn\|[p]ython.*main:app"; then
                        echo -e "${GREEN}✓ Processo Python/uvicorn está rodando${NC}"
                    else
                        echo -e "${RED}✗ Processo Python/uvicorn NÃO está rodando${NC}"
                    fi
                fi
            else
                echo -e "${RED}✗ Container não está rodando (Status: $CONTAINER_STATUS)${NC}"
            fi
    else
        echo -e "${RED}✗ Container do backend não encontrado${NC}"
    fi
else
    echo -e "${RED}✗ Nenhuma task do backend rodando${NC}"
fi

echo ""

# 6. Verificar conexão do NPM com backend
echo "6. Verificando conectividade NPM -> Backend..."
NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}' | head -n 1)

if [ -n "$NPM_SERVICE" ]; then
    NPM_TASK=$(docker service ps "$NPM_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    if [ -n "$NPM_TASK" ]; then
        NPM_CONTAINER=$(docker ps --filter "name=$NPM_TASK" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$NPM_CONTAINER" ]; then
            echo "   Testando conexão do NPM para $BACKEND_SERVICE:8001..."
            
            if docker exec "$NPM_CONTAINER" which curl > /dev/null 2>&1; then
                NPM_TO_BACKEND=$(docker exec "$NPM_CONTAINER" curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$BACKEND_SERVICE:8001/health 2>/dev/null)
                
                if [ "$NPM_TO_BACKEND" = "200" ]; then
                    echo -e "${GREEN}✓ NPM consegue alcançar o backend!${NC}"
                elif [ -n "$NPM_TO_BACKEND" ] && [ "$NPM_TO_BACKEND" != "000" ]; then
                    echo -e "${YELLOW}⚠ NPM alcançou o backend, mas retornou HTTP $NPM_TO_BACKEND${NC}"
                else
                    echo -e "${RED}✗ NPM NÃO consegue alcançar o backend${NC}"
                    echo "   Verifique se o NPM está na rede nginx_public"
                    echo "   Verifique se o nome do serviço no NPM está correto: $BACKEND_SERVICE"
                fi
            else
                echo -e "${YELLOW}⚠ curl não disponível no container NPM${NC}"
                echo "   Tentando ping..."
                if docker exec "$NPM_CONTAINER" ping -c 1 "$BACKEND_SERVICE" > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ NPM consegue fazer ping no backend${NC}"
                else
                    echo -e "${RED}✗ NPM NÃO consegue fazer ping no backend${NC}"
                fi
            fi
        fi
    fi
fi

echo ""

# 7. Verificar banco de dados
echo "7. Verificando conexão com banco de dados..."
DB_ERRORS=$(docker service logs "$BACKEND_SERVICE" 2>&1 | grep -i "database\|connection\|postgres\|error" | tail -5)

if echo "$DB_ERRORS" | grep -qi "error\|failed\|refused\|timeout"; then
    echo -e "${RED}✗ Possíveis erros de conexão com banco:${NC}"
    echo "$DB_ERRORS"
else
    echo -e "${GREEN}✓ Nenhum erro de conexão com banco detectado nos logs recentes${NC}"
fi

echo ""

# 8. Resumo e recomendações
echo "=========================================="
echo "RECOMENDAÇÕES"
echo "=========================================="
echo ""

if echo "$BACKEND_REPLICAS" | grep -q "0/1"; then
    echo -e "${RED}PROBLEMA: Backend não está rodando!${NC}"
    echo ""
    echo "Soluções:"
    echo "  1. Verificar logs: docker service logs -f $BACKEND_SERVICE"
    echo "  2. Verificar se DATABASE_URL está correto no .env"
    echo "  3. Reiniciar backend: docker service update --force $BACKEND_SERVICE"
    echo ""
elif ! docker service inspect "$BACKEND_SERVICE" 2>/dev/null | grep -q "nginx_public"; then
    echo -e "${YELLOW}PROBLEMA: Backend não está na rede nginx_public!${NC}"
    echo ""
    echo "Solução:"
    echo "  docker service update --network-add nginx_public $BACKEND_SERVICE"
    echo "  Aguarde 10 segundos e teste novamente"
    echo ""
else
    echo -e "${GREEN}Backend parece estar configurado corretamente${NC}"
    echo ""
    echo "Se ainda houver 502:"
    echo "  1. Aguarde mais alguns segundos (backend pode estar iniciando)"
    echo "  2. Verifique no NPM se o proxy está configurado corretamente:"
    echo "     - Forward Hostname/IP: $BACKEND_SERVICE (nome completo do serviço)"
    echo "     - NÃO use: ma-familiar_backend ou backend"
    echo "     - Use exatamente: sistema-familiar_backend"
    echo "     - Forward Port: 8001"
    echo "  3. Reinicie o NPM: docker service update --force <serviço-npm>"
    echo ""
    echo -e "${YELLOW}⚠ IMPORTANTE: Verifique se no NPM o Forward Hostname está como:${NC}"
    echo -e "${YELLOW}   sistema-familiar_backend${NC}"
    echo -e "${YELLOW}   (não ma-familiar_backend ou backend)${NC}"
    echo ""
fi

echo "Para ver logs em tempo real:"
echo "  docker service logs -f $BACKEND_SERVICE"
echo ""

