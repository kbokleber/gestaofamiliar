#!/bin/bash

echo "=========================================="
echo "CONECTANDO NPM À REDE nginx_public"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se a rede existe
echo "Verificando se a rede nginx_public existe..."
if ! docker network ls | grep -q "nginx_public"; then
    echo -e "${RED}ERRO: Rede nginx_public não encontrada!${NC}"
    echo "Criando rede nginx_public..."
    docker network create nginx_public
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rede nginx_public criada${NC}"
    else
        echo -e "${RED}ERRO: Não foi possível criar a rede${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Rede nginx_public encontrada${NC}"
fi

echo ""

# Identificar container do NPM
echo "Identificando container do NPM..."
NPM_CONTAINER=$(docker ps --filter "name=nginx_app" --format "{{.ID}}" | head -n 1)

if [ -z "$NPM_CONTAINER" ]; then
    echo -e "${RED}ERRO: Container do NPM não encontrado!${NC}"
    echo "Procurando por containers com 'nginx' no nome..."
    docker ps --filter "name=nginx" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}"
    echo ""
    echo "Por favor, informe o ID ou nome do container do NPM:"
    read -r NPM_CONTAINER
fi

if [ -z "$NPM_CONTAINER" ]; then
    echo -e "${RED}ERRO: Container do NPM não especificado${NC}"
    exit 1
fi

NPM_NAME=$(docker ps --filter "id=$NPM_CONTAINER" --format "{{.Names}}")
echo -e "${GREEN}✓ Container encontrado: $NPM_NAME (ID: $NPM_CONTAINER)${NC}"

echo ""

# Verificar se já está na rede
echo "Verificando se NPM já está na rede nginx_public..."
if docker inspect "$NPM_CONTAINER" | grep -q "nginx_public"; then
    echo -e "${YELLOW}⚠ NPM já está na rede nginx_public${NC}"
    echo "Verificando conectividade..."
    
    # Testar conectividade
    BACKEND_IP=$(docker inspect sistema-familiar_backend.1.* --format '{{range .NetworkSettings.Networks}}{{if eq .NetworkID (docker network inspect nginx_public --format "{{.Id}}")}}{{.IPAddress}}{{end}}{{end}}' 2>/dev/null | head -n 1)
    
    if [ -n "$BACKEND_IP" ]; then
        echo -e "${GREEN}✓ Backend encontrado na rede: $BACKEND_IP${NC}"
        echo "Testando ping do NPM para o backend..."
        if docker exec "$NPM_CONTAINER" ping -c 1 "$BACKEND_IP" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Conectividade OK!${NC}"
            exit 0
        else
            echo -e "${YELLOW}⚠ Ping falhou, mas pode ser normal (ping pode estar desabilitado)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ NPM NÃO está na rede nginx_public${NC}"
fi

echo ""

# Conectar NPM à rede
echo "Conectando NPM à rede nginx_public..."
docker network connect nginx_public "$NPM_CONTAINER"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ NPM conectado à rede nginx_public com sucesso!${NC}"
else
    echo -e "${RED}ERRO: Não foi possível conectar NPM à rede${NC}"
    exit 1
fi

echo ""

# Verificar conexão
echo "Verificando conexão..."
sleep 2

if docker inspect "$NPM_CONTAINER" | grep -q "nginx_public"; then
    echo -e "${GREEN}✓ Verificação confirmada: NPM está na rede nginx_public${NC}"
else
    echo -e "${RED}ERRO: Verificação falhou${NC}"
    exit 1
fi

echo ""

# Mostrar IPs na rede
echo "IPs na rede nginx_public:"
docker network inspect nginx_public --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}'

echo ""
echo -e "${GREEN}=========================================="
echo "CONCLUÍDO!"
echo "==========================================${NC}"
echo ""
echo "Próximos passos:"
echo "1. Reinicie o NPM: docker restart $NPM_CONTAINER"
echo "2. Teste a conectividade: ./testar-conectividade-npm.sh"
echo "3. Verifique o proxy no NPM (deve usar: sistema-familiar_backend:8001)"

