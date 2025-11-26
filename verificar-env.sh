#!/bin/bash

echo "=========================================="
echo "VERIFICANDO CONFIGURAÇÃO .env"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Verificar se .env existe
echo "1. Verificando arquivo .env..."
if [ ! -f .env ]; then
    echo -e "${RED}✗ Arquivo .env não encontrado!${NC}"
    echo ""
    echo "Criando arquivo .env a partir de .env.example (se existir)..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ Arquivo .env criado. POR FAVOR, EDITE COM SUAS CONFIGURAÇÕES!${NC}"
    else
        echo -e "${RED}✗ Arquivo .env.example também não encontrado!${NC}"
        echo "Criando .env básico..."
        cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_banco

# Security
SECRET_KEY=sua-chave-secreta-aqui

# Algorithm
ALGORITHM=HS256

# Token
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
        echo -e "${YELLOW}⚠ Arquivo .env criado com valores padrão. EDITE COM SUAS CONFIGURAÇÕES!${NC}"
    fi
    exit 1
else
    echo -e "${GREEN}✓ Arquivo .env encontrado${NC}"
fi

echo ""

# 2. Verificar variáveis essenciais
echo "2. Verificando variáveis essenciais..."

MISSING_VARS=()
EMPTY_VARS=()

# Verificar DATABASE_URL
if ! grep -q "^DATABASE_URL=" .env; then
    MISSING_VARS+=("DATABASE_URL")
elif grep -q "^DATABASE_URL=$" .env || grep -q "^DATABASE_URL=\s*$" .env; then
    EMPTY_VARS+=("DATABASE_URL")
elif grep -q "DATABASE_URL=postgresql://usuario:senha" .env || grep -q "DATABASE_URL=postgresql://postgres:postgres" .env; then
    echo -e "${YELLOW}⚠ DATABASE_URL parece ter valores padrão/exemplo${NC}"
    EMPTY_VARS+=("DATABASE_URL (valores padrão)")
else
    DATABASE_URL_VALUE=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$DATABASE_URL_VALUE" ]; then
        EMPTY_VARS+=("DATABASE_URL")
    else
        echo -e "${GREEN}✓ DATABASE_URL configurado${NC}"
        # Mostrar apenas o início da URL (sem senha)
        DB_DISPLAY=$(echo "$DATABASE_URL_VALUE" | sed 's/:[^:@]*@/:***@/')
        echo "   Valor: $DB_DISPLAY"
    fi
fi

# Verificar SECRET_KEY
if ! grep -q "^SECRET_KEY=" .env; then
    MISSING_VARS+=("SECRET_KEY")
elif grep -q "^SECRET_KEY=$" .env || grep -q "^SECRET_KEY=\s*$" .env; then
    EMPTY_VARS+=("SECRET_KEY")
elif grep -q "SECRET_KEY=sua-chave-secreta" .env || grep -q "SECRET_KEY=your-secret-key" .env; then
    echo -e "${YELLOW}⚠ SECRET_KEY parece ter valores padrão/exemplo${NC}"
    EMPTY_VARS+=("SECRET_KEY (valores padrão)")
else
    SECRET_KEY_VALUE=$(grep "^SECRET_KEY=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$SECRET_KEY_VALUE" ]; then
        EMPTY_VARS+=("SECRET_KEY")
    else
        echo -e "${GREEN}✓ SECRET_KEY configurado${NC}"
        SECRET_LENGTH=${#SECRET_KEY_VALUE}
        echo "   Tamanho: $SECRET_LENGTH caracteres"
    fi
fi

echo ""

# 3. Mostrar problemas encontrados
if [ ${#MISSING_VARS[@]} -gt 0 ] || [ ${#EMPTY_VARS[@]} -gt 0 ]; then
    echo -e "${RED}✗ PROBLEMAS ENCONTRADOS:${NC}"
    echo ""
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo "Variáveis faltando:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        echo ""
    fi
    
    if [ ${#EMPTY_VARS[@]} -gt 0 ]; then
        echo "Variáveis vazias ou com valores padrão:"
        for var in "${EMPTY_VARS[@]}"; do
            echo "  - $var"
        done
        echo ""
    fi
    
    echo "=========================================="
    echo "SOLUÇÃO"
    echo "=========================================="
    echo ""
    echo "Edite o arquivo .env e configure:"
    echo ""
    
    if [[ " ${MISSING_VARS[@]} ${EMPTY_VARS[@]} " =~ " DATABASE_URL " ]]; then
        echo "1. DATABASE_URL:"
        echo "   Formato: postgresql://usuario:senha@host:porta/nome_banco"
        echo "   Exemplo: postgresql://postgres:minhasenha@postgres-container:5432/sistema_familiar"
        echo "   OU se o banco estiver em outro servidor:"
        echo "   Exemplo: postgresql://postgres:minhasenha@192.168.1.100:5432/sistema_familiar"
        echo ""
    fi
    
    if [[ " ${MISSING_VARS[@]} ${EMPTY_VARS[@]} " =~ " SECRET_KEY " ]]; then
        echo "2. SECRET_KEY:"
        echo "   Gere uma chave secreta com:"
        echo "   openssl rand -hex 32"
        echo "   OU"
        echo "   python -c 'import secrets; print(secrets.token_hex(32))'"
        echo ""
    fi
    
    echo "Depois de editar o .env, execute:"
    echo "  docker stack rm sistema-familiar"
    echo "  ./redeploy-seguro.sh"
    echo ""
    
    exit 1
else
    echo -e "${GREEN}✓ Todas as variáveis essenciais estão configuradas${NC}"
fi

echo ""

# 4. Verificar se as variáveis estão sendo carregadas no stack
echo "3. Verificando se variáveis estão no stack..."
STACK_NAME="sistema-familiar"
BACKEND_SERVICE="${STACK_NAME}_backend"

if docker service ls | grep -q "$BACKEND_SERVICE"; then
    echo "   Verificando variáveis de ambiente do serviço backend..."
    
    # Tentar obter DATABASE_URL do serviço
    SERVICE_ENV=$(docker service inspect "$BACKEND_SERVICE" --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' 2>/dev/null)
    
    if echo "$SERVICE_ENV" | grep -q "DATABASE_URL="; then
        DB_URL_IN_SERVICE=$(echo "$SERVICE_ENV" | grep "DATABASE_URL=" | cut -d'=' -f2-)
        if [ -z "$DB_URL_IN_SERVICE" ]; then
            echo -e "${RED}✗ DATABASE_URL está vazio no serviço!${NC}"
            echo ""
            echo "Solução:"
            echo "  1. Verifique se o .env está correto"
            echo "  2. Remova e redeploy o stack:"
            echo "     docker stack rm sistema-familiar"
            echo "     ./redeploy-seguro.sh"
        else
            echo -e "${GREEN}✓ DATABASE_URL está presente no serviço${NC}"
        fi
    else
        echo -e "${RED}✗ DATABASE_URL não encontrado no serviço!${NC}"
        echo ""
        echo "Solução:"
        echo "  docker stack rm sistema-familiar"
        echo "  ./redeploy-seguro.sh"
    fi
else
    echo -e "${YELLOW}⚠ Serviço backend não encontrado (stack pode não estar deployado)${NC}"
fi

echo ""

# 5. Resumo
echo "=========================================="
echo "RESUMO"
echo "=========================================="
echo ""

if [ ${#MISSING_VARS[@]} -eq 0 ] && [ ${#EMPTY_VARS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ Configuração do .env está OK${NC}"
    echo ""
    echo "Se o backend ainda não está iniciando, verifique:"
    echo "  1. Se o banco de dados está acessível"
    echo "  2. Se a rede db_network existe e o backend está conectado"
    echo "  3. Logs do backend: docker service logs -f sistema-familiar_backend"
else
    echo -e "${RED}✗ Configuração do .env precisa ser corrigida${NC}"
    echo ""
    echo "Edite o arquivo .env e execute este script novamente."
fi

echo ""

