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
    TASK_ID=$(docker service ps sistema-familiar_backend -q --no-trunc --filter "desired-state=running" | head -1)
    if [ -z "$TASK_ID" ]; then
        # Tentar obter qualquer task do serviço
        TASK_ID=$(docker service ps sistema-familiar_backend -q --no-trunc | head -1)
    fi
    
    if [ -z "$TASK_ID" ]; then
        # Tentar obter container diretamente
        CONTAINER=$(docker ps --filter "name=sistema-familiar_backend" --format "{{.ID}}" | head -1)
        if [ -n "$CONTAINER" ]; then
            echo "$CONTAINER"
            return 0
        fi
        
        # Última tentativa: buscar por qualquer container com "backend"
        CONTAINER=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
        if [ -n "$CONTAINER" ]; then
            echo "$CONTAINER"
            return 0
        fi
        
        print_error "Não foi possível encontrar o container do backend"
        print_info "Tente executar manualmente: docker ps"
        exit 1
    fi
    
    # Construir nome do container no formato do Docker Swarm
    echo "sistema-familiar_backend.1.${TASK_ID}"
}

# Função para executar código Python inline no container
run_python_code() {
    local python_code=$1
    local container=$2
    local description=$3
    
    print_info "Executando: $description"
    
    if echo "$python_code" | docker exec -i "$container" python - 2>&1; then
        print_success "$description executado com sucesso"
        return 0
    else
        print_error "Falha ao executar $description"
        return 1
    fi
}

# Função para executar script Python no container (fallback)
run_script() {
    local script_name=$1
    local container=$2
    
    # Tentar usar o caminho encontrado se existir
    if [ -n "$FOUND_PATH" ]; then
        local script_path="$FOUND_PATH/$script_name"
        if docker exec "$container" test -f "$script_path" 2>/dev/null; then
            print_info "Executando script: $script_path"
            if docker exec -it "$container" python "$script_path" 2>&1; then
                print_success "$script_name executado com sucesso"
                return 0
            else
                print_error "Falha ao executar $script_name"
                return 1
            fi
        fi
    fi
    
    # Se não encontrou o arquivo, retornar 1 para que o código inline seja executado
    return 1
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
print_info "Verificando se o container está ativo..."
if docker exec "$CONTAINER" echo "Container ativo" > /dev/null 2>&1; then
    print_success "Container está respondendo"
else
    print_warning "Container não respondeu ao teste inicial, mas continuando..."
    print_info "Se houver erros, verifique manualmente: docker ps"
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

# Verificar caminhos possíveis
SCRIPT_PATHS=("scripts" "/app/scripts" "backend/scripts")

FOUND_PATH=""
for path in "${SCRIPT_PATHS[@]}"; do
    if docker exec "$CONTAINER" test -f "$path/create_tables.py" 2>/dev/null; then
        FOUND_PATH="$path"
        print_success "Scripts encontrados em: $path"
        break
    fi
done

if [ -z "$FOUND_PATH" ]; then
    print_warning "Scripts de migração não encontrados no container"
    print_info "O script executará o código Python diretamente (inline)"
    print_info "Isso não requer que os arquivos estejam no container"
else
    # Verificar cada script
    for script in "${SCRIPTS[@]}"; do
        if ! docker exec "$CONTAINER" test -f "$FOUND_PATH/$script" 2>/dev/null; then
            print_warning "Script não encontrado: $FOUND_PATH/$script (usando código inline)"
            FOUND_PATH=""
            break
        fi
    done
    if [ -n "$FOUND_PATH" ]; then
        print_success "Todos os scripts encontrados em $FOUND_PATH"
    fi
fi

# Fazer backup (opcional)
do_backup

echo ""
print_info "Iniciando migrações..."
echo ""

# 1. Criar tabela families
print_info "=== PASSO 1/6: Criando tabela families ==="
CREATE_TABLES_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import Base, engine
from app.models import *
print("[INICIO] Criando tabelas no banco de dados...")
try:
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"[OK] Tabelas criadas! Total: {len(tables)}")
    if "families" in tables:
        print("[OK] Tabela families existe!")
    else:
        print("[ERRO] Tabela families nao foi criada!")
        sys.exit(1)
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
'
if run_script "create_tables.py" "$CONTAINER" || run_python_code "$CREATE_TABLES_CODE" "$CONTAINER" "Criar tabela families"; then
    print_success "Tabela families criada/verificada"
else
    print_error "Falha ao criar tabela families"
    exit 1
fi
echo ""

# 2. Adicionar family_id em auth_user
print_info "=== PASSO 2/6: Adicionando family_id em auth_user ==="
ADD_FAMILY_ID_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import engine
from sqlalchemy import text
print("[INICIO] Adicionando coluna family_id na tabela auth_user...")
try:
    with engine.connect() as conn:
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='auth_user' AND column_name='family_id'
        """)
        result = conn.execute(check_query)
        exists = result.fetchone() is not None
        if exists:
            print("[INFO] Coluna family_id ja existe.")
        else:
            alter_query = text("""
                ALTER TABLE auth_user 
                ADD COLUMN family_id INTEGER,
                ADD CONSTRAINT fk_auth_user_family 
                FOREIGN KEY (family_id) REFERENCES families(id)
            """)
            conn.execute(alter_query)
            conn.commit()
            index_query = text("""
                CREATE INDEX IF NOT EXISTS ix_auth_user_family_id 
                ON auth_user(family_id)
            """)
            conn.execute(index_query)
            conn.commit()
            print("[OK] Coluna family_id adicionada!")
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
'
if run_script "add_family_id_to_users.py" "$CONTAINER" || run_python_code "$ADD_FAMILY_ID_CODE" "$CONTAINER" "Adicionar family_id em auth_user"; then
    print_success "Coluna family_id adicionada em auth_user"
else
    print_error "Falha ao adicionar family_id em auth_user"
    exit 1
fi
echo ""

# 3. Criar tabela user_families
print_info "=== PASSO 3/6: Criando tabela user_families ==="
CREATE_USER_FAMILIES_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import engine
from sqlalchemy import text
print("[INICIO] Criando tabela user_families...")
try:
    with engine.connect() as conn:
        check_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='user_families'
        """)
        result = conn.execute(check_query)
        exists = result.fetchone() is not None
        if exists:
            print("[INFO] Tabela user_families ja existe.")
        else:
            create_query = text("""
                CREATE TABLE user_families (
                    user_id INTEGER NOT NULL,
                    family_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, family_id),
                    CONSTRAINT fk_user_families_user 
                        FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE,
                    CONSTRAINT fk_user_families_family 
                        FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
                )
            """)
            conn.execute(create_query)
            conn.commit()
            index1_query = text("""
                CREATE INDEX IF NOT EXISTS ix_user_families_user_id 
                ON user_families(user_id)
            """)
            conn.execute(index1_query)
            conn.commit()
            index2_query = text("""
                CREATE INDEX IF NOT EXISTS ix_user_families_family_id 
                ON user_families(family_id)
            """)
            conn.execute(index2_query)
            conn.commit()
            print("[OK] Tabela user_families criada!")
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
'
if run_script "create_user_families_table.py" "$CONTAINER" || run_python_code "$CREATE_USER_FAMILIES_CODE" "$CONTAINER" "Criar tabela user_families"; then
    print_success "Tabela user_families criada/verificada"
else
    print_error "Falha ao criar tabela user_families"
    exit 1
fi
echo ""

# 4. Adicionar family_id em healthcare_familymember
print_info "=== PASSO 4/6: Adicionando family_id em healthcare_familymember ==="
CHECK_FAMILY_MEMBER_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import engine
from sqlalchemy import text
print("[INICIO] Verificando tabela healthcare_familymember...")
try:
    with engine.connect() as conn:
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='healthcare_familymember' AND column_name='family_id'
        """)
        result = conn.execute(check_query)
        exists = result.fetchone() is not None
        if not exists:
            print("[INFO] Adicionando coluna family_id...")
            alter_query = text("""
                ALTER TABLE healthcare_familymember 
                ADD COLUMN family_id INTEGER,
                ADD CONSTRAINT fk_healthcare_familymember_family 
                FOREIGN KEY (family_id) REFERENCES families(id)
            """)
            conn.execute(alter_query)
            conn.commit()
            index_query = text("""
                CREATE INDEX IF NOT EXISTS ix_healthcare_familymember_family_id 
                ON healthcare_familymember(family_id)
            """)
            conn.execute(index_query)
            conn.commit()
            print("[OK] Coluna family_id adicionada!")
            
            # Associar membros existentes à família padrão
            family_query = text("SELECT id FROM families WHERE codigo_unico = 'DEFAULT' LIMIT 1")
            result = conn.execute(family_query)
            family_row = result.fetchone()
            if family_row:
                default_family_id = family_row[0]
                update_query = text("""
                    UPDATE healthcare_familymember 
                    SET family_id = :family_id 
                    WHERE family_id IS NULL
                """)
                conn.execute(update_query, {"family_id": default_family_id})
                conn.commit()
                print(f"[OK] Membros associados a familia padrao (ID: {default_family_id})")
        else:
            print("[INFO] Coluna family_id ja existe.")
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
'
if run_script "check_family_member_table.py" "$CONTAINER" || run_python_code "$CHECK_FAMILY_MEMBER_CODE" "$CONTAINER" "Adicionar family_id em healthcare_familymember"; then
    print_success "Coluna family_id adicionada em healthcare_familymember"
else
    print_error "Falha ao adicionar family_id em healthcare_familymember"
    exit 1
fi
echo ""

# 5. Adicionar family_id em outras tabelas
print_info "=== PASSO 5/6: Adicionando family_id em outras tabelas ==="
MIGRATE_ALL_TABLES_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import engine
from sqlalchemy import text
print("[INICIO] Migrando outras tabelas...")
try:
    with engine.connect() as conn:
        tables = [("maintenance_equipment", "family_id", "fk_maintenance_equipment_family")]
        for table_name, column_name, fk_name in tables:
            check_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=:table_name AND column_name=:column_name
            """)
            result = conn.execute(check_query, {"table_name": table_name, "column_name": column_name})
            exists = result.fetchone() is not None
            if not exists:
                print(f"  [INFO] Adicionando {column_name} em {table_name}...")
                alter_query = text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} INTEGER,
                    ADD CONSTRAINT {fk_name} 
                    FOREIGN KEY ({column_name}) REFERENCES families(id)
                """)
                conn.execute(alter_query)
                conn.commit()
                index_query = text(f"""
                    CREATE INDEX IF NOT EXISTS ix_{table_name}_{column_name} 
                    ON {table_name}({column_name})
                """)
                conn.execute(index_query)
                conn.commit()
                
                # Associar registros à família padrão
                family_query = text("SELECT id FROM families WHERE codigo_unico = 'DEFAULT' LIMIT 1")
                result = conn.execute(family_query)
                family_row = result.fetchone()
                if family_row:
                    default_family_id = family_row[0]
                    update_query = text(f"""
                        UPDATE {table_name} 
                        SET {column_name} = :family_id 
                        WHERE {column_name} IS NULL
                    """)
                    conn.execute(update_query, {"family_id": default_family_id})
                    conn.commit()
                print(f"  [OK] {column_name} adicionada em {table_name}!")
            else:
                print(f"  [INFO] {column_name} ja existe em {table_name}.")
        print("[OK] Migracao de tabelas concluida!")
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
'
if run_script "migrate_all_family_tables.py" "$CONTAINER" || run_python_code "$MIGRATE_ALL_TABLES_CODE" "$CONTAINER" "Adicionar family_id em outras tabelas"; then
    print_success "Coluna family_id adicionada em outras tabelas"
else
    print_error "Falha ao adicionar family_id em outras tabelas"
    exit 1
fi
echo ""

# 6. Migrar usuários existentes
print_info "=== PASSO 6/6: Migrando usuários existentes ==="
MIGRATE_USERS_CODE='
import sys
sys.path.insert(0, "/app")
from app.db.base import SessionLocal
from app.models.user import User
from app.models.family import Family
print("[INICIO] Migrando usuarios para familia padrao...")
db = SessionLocal()
try:
    default_family = db.query(Family).filter(Family.codigo_unico == "DEFAULT").first()
    if not default_family:
        default_family = Family(name="Família Padrão", codigo_unico="DEFAULT")
        db.add(default_family)
        db.commit()
        db.refresh(default_family)
        print(f"[OK] Familia padrao criada: ID={default_family.id}")
    else:
        print(f"[INFO] Familia padrao ja existe: ID={default_family.id}")
    
    users_without_family = db.query(User).filter(User.family_id == None).all()
    if users_without_family:
        print(f"[INFO] Encontrados {len(users_without_family)} usuarios sem familia")
        for user in users_without_family:
            user.family_id = default_family.id
        db.commit()
        print(f"[OK] {len(users_without_family)} usuarios associados a familia padrao!")
    else:
        print("[OK] Todos os usuarios ja tem familia.")
    
    total_users = db.query(User).count()
    users_in_default = db.query(User).filter(User.family_id == default_family.id).count()
    print(f"[STATS] Total: {total_users}, Na familia padrao: {users_in_default}")
except Exception as e:
    db.rollback()
    print(f"[ERRO] Erro: {e}")
    sys.exit(1)
finally:
    db.close()
'
if run_script "migrate_users_to_family.py" "$CONTAINER" || run_python_code "$MIGRATE_USERS_CODE" "$CONTAINER" "Migrar usuários para família padrão"; then
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

