#!/bin/bash

echo "=========================================="
echo "TESTANDO CARREGAMENTO DE VARIÁVEIS"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar se .env existe
if [ ! -f .env ]; then
    echo -e "${RED}✗ Arquivo .env não encontrado!${NC}"
    exit 1
fi

echo "1. Lendo arquivo .env..."
cat .env | head -5
echo ""

# Carregar variáveis (mesmo método do deploy.sh)
echo "2. Carregando variáveis..."
TMP_ENV=$(mktemp)
while IFS= read -r line || [ -n "$line" ]; do
    if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
        line="${line%%#*}"
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if [[ -n "$line" && "$line" =~ ^[^=]+=.+$ ]]; then
            echo "$line" >> "$TMP_ENV"
        fi
    fi
done < .env

set -a
source "$TMP_ENV" 2>/dev/null || true
set +a
rm -f "$TMP_ENV"

echo "3. Verificando variáveis carregadas:"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL está vazia${NC}"
else
    echo -e "${GREEN}✓ DATABASE_URL carregada${NC}"
    echo "   Valor: ${DATABASE_URL:0:50}..."
fi

if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}✗ SECRET_KEY está vazia${NC}"
else
    echo -e "${GREEN}✓ SECRET_KEY carregada${NC}"
    echo "   Tamanho: ${#SECRET_KEY} caracteres"
fi

echo ""
echo "4. Testando se variáveis estão exportadas:"
export | grep -E "DATABASE_URL|SECRET_KEY" | head -2

echo ""
echo "5. Verificando variáveis no serviço Docker (se existir):"
BACKEND_SERVICE="sistema-familiar_backend"
if docker service ls | grep -q "$BACKEND_SERVICE"; then
    echo "   Variáveis de ambiente no serviço:"
    docker service inspect "$BACKEND_SERVICE" --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' 2>/dev/null | grep -E "DATABASE_URL|SECRET_KEY" || echo "   Nenhuma variável encontrada"
else
    echo "   Serviço não encontrado"
fi

echo ""

