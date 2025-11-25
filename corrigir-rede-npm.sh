#!/bin/bash

echo "=========================================="
echo "CORRIGINDO REDE DO NPM"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Verificar se a rede nginx_public existe
echo "1. Verificando rede nginx_public..."
if docker network ls | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Rede nginx_public existe${NC}"
    NETWORK_ID=$(docker network inspect nginx_public --format "{{.Id}}")
    echo "   ID da rede: $NETWORK_ID"
else
    echo -e "${RED}✗ Rede nginx_public NÃO existe!${NC}"
    echo ""
    echo "Criando rede nginx_public..."
    docker network create nginx_public
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rede criada${NC}"
    else
        echo -e "${RED}ERRO: Não foi possível criar a rede${NC}"
        exit 1
    fi
fi

echo ""

# 2. Verificar stack do NPM
echo "2. Verificando stack do NPM..."
NPM_STACK=$(docker stack ls | grep -i nginx | awk '{print $1}' | head -n 1)

if [ -z "$NPM_STACK" ]; then
    echo -e "${YELLOW}⚠ Nenhum stack do NPM encontrado${NC}"
    echo "   Procurando por containers do NPM..."
    NPM_CONTAINER=$(docker ps --filter "ancestor=jc21/nginx-proxy-manager:latest" --format "{{.ID}}" | head -n 1)
    
    if [ -z "$NPM_CONTAINER" ]; then
        echo -e "${RED}✗ Container do NPM não encontrado!${NC}"
        echo ""
        echo "Por favor, verifique se o NPM está rodando:"
        echo "  docker ps | grep nginx"
        exit 1
    fi
    
    NPM_NAME=$(docker ps --filter "id=$NPM_CONTAINER" --format "{{.Names}}")
    echo -e "${YELLOW}⚠ Container encontrado: $NPM_NAME (não está em um stack)${NC}"
    NPM_IN_STACK=false
else
    echo -e "${GREEN}✓ Stack do NPM encontrado: $NPM_STACK${NC}"
    NPM_SERVICE=$(docker service ls | grep -i nginx | grep -i app | awk '{print $1}' | head -n 1)
    if [ -n "$NPM_SERVICE" ]; then
        echo -e "${GREEN}✓ Serviço do NPM: $NPM_SERVICE${NC}"
    fi
    NPM_IN_STACK=true
fi

echo ""

# 3. Verificar se NPM está na rede nginx_public
echo "3. Verificando se NPM está na rede nginx_public..."

if [ "$NPM_IN_STACK" = true ]; then
    # Se está em um stack, verificar via service
    if [ -n "$NPM_SERVICE" ]; then
        NPM_TASK=$(docker service ps "$NPM_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
        if [ -n "$NPM_TASK" ]; then
            NPM_CONTAINER=$(docker ps --filter "name=$NPM_TASK" --format "{{.ID}}" | head -n 1)
        fi
    fi
fi

if [ -z "$NPM_CONTAINER" ]; then
    echo -e "${RED}✗ Não foi possível identificar o container do NPM${NC}"
    exit 1
fi

NPM_NAME=$(docker ps --filter "id=$NPM_CONTAINER" --format "{{.Names}}")
echo "   Container: $NPM_NAME"

# Verificar redes do NPM
NPM_NETWORKS=$(docker inspect "$NPM_CONTAINER" --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}')

if echo "$NPM_NETWORKS" | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ NPM está na rede nginx_public${NC}"
    NPM_IN_NETWORK=true
else
    echo -e "${RED}✗ NPM NÃO está na rede nginx_public${NC}"
    echo "   Redes atuais: $NPM_NETWORKS"
    NPM_IN_NETWORK=false
fi

echo ""

# 4. Verificar backend
echo "4. Verificando backend do sistema-familiar..."
BACKEND_SERVICE="sistema-familiar_backend"
if docker service ls | grep -q "$BACKEND_SERVICE"; then
    echo -e "${GREEN}✓ Serviço backend encontrado${NC}"
    
    BACKEND_TASK=$(docker service ps "$BACKEND_SERVICE" --format "{{.Name}}" --filter "desired-state=running" | head -n 1)
    if [ -n "$BACKEND_TASK" ]; then
        BACKEND_CONTAINER=$(docker ps --filter "name=$BACKEND_TASK" --format "{{.ID}}" | head -n 1)
        if [ -n "$BACKEND_CONTAINER" ]; then
            BACKEND_NAME=$(docker ps --filter "id=$BACKEND_CONTAINER" --format "{{.Names}}")
            echo "   Container: $BACKEND_NAME"
            
            BACKEND_NETWORKS=$(docker inspect "$BACKEND_CONTAINER" --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}')
            if echo "$BACKEND_NETWORKS" | grep -q "nginx_public"; then
                echo -e "${GREEN}✓ Backend está na rede nginx_public${NC}"
                
                # Obter IP do backend na rede
                BACKEND_IP=$(docker inspect "$BACKEND_CONTAINER" --format '{{range .NetworkSettings.Networks}}{{if eq .NetworkID "'"$NETWORK_ID"'"}}{{.IPAddress}}{{end}}{{end}}')
                if [ -n "$BACKEND_IP" ]; then
                    echo "   IP do backend: $BACKEND_IP"
                fi
            else
                echo -e "${RED}✗ Backend NÃO está na rede nginx_public${NC}"
                echo "   Redes atuais: $BACKEND_NETWORKS"
            fi
        fi
    fi
else
    echo -e "${RED}✗ Serviço backend não encontrado${NC}"
fi

echo ""

# 5. Aplicar correções
echo "5. Aplicando correções..."

if [ "$NPM_IN_NETWORK" = false ]; then
    echo -e "${YELLOW}⚠ Conectando NPM à rede nginx_public...${NC}"
    
    if [ "$NPM_IN_STACK" = true ]; then
        echo -e "${BLUE}   NPM está em um stack. Recomendado: redeployar o stack do NPM${NC}"
        echo ""
        echo "   Opções:"
        echo "   a) Redeployar stack do NPM (recomendado):"
        echo "      docker stack rm $NPM_STACK"
        echo "      # Aguardar alguns segundos"
        echo "      docker stack deploy -c <seu-docker-compose-npm.yml> $NPM_STACK"
        echo ""
        echo "   b) Conectar manualmente (temporário):"
        read -p "   Conectar manualmente agora? (s/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            docker network connect nginx_public "$NPM_CONTAINER"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ NPM conectado manualmente${NC}"
                echo -e "${YELLOW}⚠ ATENÇÃO: Esta conexão será perdida se o container reiniciar${NC}"
                echo -e "${YELLOW}⚠ Recomendado: redeployar o stack do NPM${NC}"
            else
                echo -e "${RED}✗ Falha ao conectar${NC}"
            fi
        fi
    else
        # NPM não está em stack, pode conectar diretamente
        docker network connect nginx_public "$NPM_CONTAINER"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ NPM conectado à rede${NC}"
        else
            echo -e "${RED}✗ Falha ao conectar${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ NPM já está na rede${NC}"
fi

echo ""

# 6. Resumo e próximos passos
echo "=========================================="
echo "RESUMO"
echo "=========================================="
echo ""

if [ "$NPM_IN_NETWORK" = true ] || [ "$NPM_IN_NETWORK" = false ] && docker inspect "$NPM_CONTAINER" | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ NPM está na rede nginx_public${NC}"
    
    echo ""
    echo "Próximos passos:"
    echo "1. Reiniciar o NPM para garantir que a rede está ativa:"
    if [ "$NPM_IN_STACK" = true ]; then
        echo "   docker service update --force $NPM_SERVICE"
    else
        echo "   docker restart $NPM_CONTAINER"
    fi
    echo ""
    echo "2. Aguardar alguns segundos e testar:"
    echo "   ./testar-conectividade-npm.sh"
    echo ""
    echo "3. Verificar no NPM (porta 81):"
    echo "   - Proxy Host deve usar: sistema-familiar_backend:8001"
    echo "   - Não usar IP, usar o nome do serviço"
else
    echo -e "${RED}✗ NPM ainda não está na rede nginx_public${NC}"
    echo ""
    echo "Ação necessária:"
    if [ "$NPM_IN_STACK" = true ]; then
        echo "   Redeployar o stack do NPM com a configuração correta"
    else
        echo "   Verificar por que a conexão manual falhou"
    fi
fi

echo ""

