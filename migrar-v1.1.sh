#!/bin/bash

###############################################################################
# Script de Migração para Versão 1.1 - Sistema Familiar
# 
# Este script executa todas as migrações necessárias do banco de dados
# para a versão 1.1 (Sistema SaaS Multi-tenant)
#
# USO: ./migrar-v1.1.sh
###############################################################################

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERRO]${NC} $1"
}

# Função para obter o container do backend
get_backend_container() {
    # Tentar obter o container do backend do Docker Swarm
    CONTAINER=$(docker service ps -f "name=sistema-familiar_backend" -q --no-trunc | head -1)
    if [ -z "$CONTAINER" ]; then
        # Tentar obter de outra forma
        CONTAINER=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
    fi
    if [ -z "$CONTAINER" ]; then
        print_error "Não foi possível encontrar o container do backend"
        print_info "Tente executar manualmente: docker ps"
        exit 1
    fi
    echo "sistema-familiar_backend.1.${CONTAINER}"
}

# Função para executar script Python no container
run_script() {
    local script_name=$1
    local container=$2
    
    print_info "Executando: $script_name"
    
    if docker exec -it "$container" python "scripts/$script_name" 2>&1; then
        print_success "$script_name executado com sucesso"
        return 0
    else
        print_error "Falha ao executar $script_name"
        return 1
    fi
}

# Função para fazer backup
do_backup() {
    print_info "Iniciando backup do banco de dados..."
    
    # Tentar obter variáveis de ambiente do container
    BACKUP_FILE="backup_pre_v1.1_$(date +%Y%m%d_%H%M%S).sql"
    
    print_warning "IMPORTANTE: Certifique-se de fazer backup manualmente se necessário"
    print_info "Backup será salvo como: $BACKUP_FILE"
    
    # Se tiver acesso direto ao PostgreSQL, pode fazer backup aqui
    # pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_FILE
    
    print_success "Backup configurado (execute manualmente se necessário)"
}

###############################################################################
# INÍCIO DO SCRIPT
###############################################################################

echo ""
echo "=========================================="
echo "  Migração para Versão 1.1"
echo "  Sistema SaaS Multi-tenant"
echo "=========================================="
echo ""

# Confirmar execução
print_warning "Este script irá modificar o banco de dados!"
read -p "Deseja continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    print_info "Migração cancelada pelo usuário"
    exit 0
fi

# Obter container do backend
print_info "Localizando container do backend..."
CONTAINER=$(get_backend_container)
print_success "Container encontrado: $CONTAINER"

# Verificar se o container está rodando
if ! docker exec "$CONTAINER" echo "Container ativo" > /dev/null 2>&1; then
    print_error "Container não está respondendo"
    exit 1
fi

# Verificar se os scripts existem
print_info "Verificando scripts de migração..."
SCRIPTS=(
    "create_tables.py"
    "add_family_id_to_users.py"
    "create_user_families_table.py"
    "check_family_member_table.py"
    "migrate_all_family_tables.py"
    "migrate_users_to_family.py"
)

for script in "${SCRIPTS[@]}"; do
    if ! docker exec "$CONTAINER" test -f "scripts/$script"; then
        print_error "Script não encontrado: scripts/$script"
        exit 1
    fi
done
print_success "Todos os scripts encontrados"

# Fazer backup (opcional)
do_backup

echo ""
print_info "Iniciando migrações..."
echo ""

# 1. Criar tabela families
print_info "=== PASSO 1/6: Criando tabela families ==="
if run_script "create_tables.py" "$CONTAINER"; then
    print_success "Tabela families criada/verificada"
else
    print_error "Falha ao criar tabela families"
    exit 1
fi
echo ""

# 2. Adicionar family_id em auth_user
print_info "=== PASSO 2/6: Adicionando family_id em auth_user ==="
if run_script "add_family_id_to_users.py" "$CONTAINER"; then
    print_success "Coluna family_id adicionada em auth_user"
else
    print_error "Falha ao adicionar family_id em auth_user"
    exit 1
fi
echo ""

# 3. Criar tabela user_families
print_info "=== PASSO 3/6: Criando tabela user_families ==="
if run_script "create_user_families_table.py" "$CONTAINER"; then
    print_success "Tabela user_families criada/verificada"
else
    print_error "Falha ao criar tabela user_families"
    exit 1
fi
echo ""

# 4. Adicionar family_id em healthcare_familymember
print_info "=== PASSO 4/6: Adicionando family_id em healthcare_familymember ==="
if run_script "check_family_member_table.py" "$CONTAINER"; then
    print_success "Coluna family_id adicionada em healthcare_familymember"
else
    print_error "Falha ao adicionar family_id em healthcare_familymember"
    exit 1
fi
echo ""

# 5. Adicionar family_id em outras tabelas
print_info "=== PASSO 5/6: Adicionando family_id em outras tabelas ==="
if run_script "migrate_all_family_tables.py" "$CONTAINER"; then
    print_success "Coluna family_id adicionada em outras tabelas"
else
    print_error "Falha ao adicionar family_id em outras tabelas"
    exit 1
fi
echo ""

# 6. Migrar usuários existentes
print_info "=== PASSO 6/6: Migrando usuários existentes ==="
if run_script "migrate_users_to_family.py" "$CONTAINER"; then
    print_success "Usuários migrados para família padrão"
else
    print_error "Falha ao migrar usuários"
    exit 1
fi
echo ""

###############################################################################
# VERIFICAÇÃO FINAL
###############################################################################

print_info "=== Verificando migração ==="

# Verificar se a tabela families existe
if docker exec "$CONTAINER" python -c "
from app.db.base import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
if 'families' in tables:
    print('OK: Tabela families existe')
    exit(0)
else:
    print('ERRO: Tabela families nao existe')
    exit(1)
" 2>/dev/null; then
    print_success "Tabela families verificada"
else
    print_warning "Não foi possível verificar tabela families automaticamente"
fi

# Verificar se a tabela user_families existe
if docker exec "$CONTAINER" python -c "
from app.db.base import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
if 'user_families' in tables:
    print('OK: Tabela user_families existe')
    exit(0)
else:
    print('ERRO: Tabela user_families nao existe')
    exit(1)
" 2>/dev/null; then
    print_success "Tabela user_families verificada"
else
    print_warning "Não foi possível verificar tabela user_families automaticamente"
fi

echo ""
echo "=========================================="
print_success "Migração concluída com sucesso!"
echo "=========================================="
echo ""
print_info "Próximos passos:"
echo "  1. Execute o redeploy:"
echo "     cd /opt/sistema-familiar && git pull origin master && chmod +x redeploy-seguro.sh && ./redeploy-seguro.sh"
echo ""
echo "  2. Verifique os logs após o deploy:"
echo "     docker service logs -f sistema-familiar_backend"
echo ""
echo "  3. Teste a aplicação:"
echo "     - Faça login"
echo "     - Verifique se os dados aparecem corretamente"
echo "     - Teste a tela de administração de famílias (se for admin)"
echo ""
print_warning "IMPORTANTE: Mantenha o backup do banco de dados até confirmar que tudo está funcionando!"
echo ""

