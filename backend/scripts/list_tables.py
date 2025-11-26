"""
Script para listar todas as tabelas do banco de dados e identificar quais não são usadas pelo sistema
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import create_engine, inspect, text
    from app.db.base import Base
    from app.core.config import settings
except ImportError:
    # Se não conseguir importar, tentar importar do diretório pai
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, parent_dir)
    from sqlalchemy import create_engine, inspect, text
    from app.db.base import Base
    from app.core.config import settings

def get_all_tables_from_models():
    """Retorna todas as tabelas definidas nos modelos SQLAlchemy"""
    tables = set()
    
    # Importar todos os modelos para garantir que Base.metadata esteja completo
    from app.models.user import User, Profile
    from app.models.dashboard import DashboardPreference
    from app.models.family import Family
    from app.models.user_family import user_families
    from app.models.healthcare import FamilyMember, MedicalAppointment, MedicalProcedure, Medication
    from app.models.maintenance import Equipment, EquipmentAttachment, MaintenanceOrder, MaintenanceImage
    
    # Obter todas as tabelas dos modelos
    for table_name in Base.metadata.tables.keys():
        tables.add(table_name)
    
    # Adicionar tabela de relacionamento many-to-many
    tables.add(user_families.name)
    
    return tables

def get_all_tables_from_database(engine):
    """Retorna todas as tabelas existentes no banco de dados"""
    inspector = inspect(engine)
    return set(inspector.get_table_names())

def main():
    """Função principal"""
    # Criar engine
    engine = create_engine(settings.DATABASE_URL)
    
    print("=" * 80)
    print("ANÁLISE DE TABELAS DO BANCO DE DADOS")
    print("=" * 80)
    print()
    
    # Obter tabelas dos modelos
    model_tables = get_all_tables_from_models()
    print(f"📋 Tabelas definidas nos modelos ({len(model_tables)}):")
    for table in sorted(model_tables):
        print(f"   ✓ {table}")
    print()
    
    # Obter tabelas do banco
    db_tables = get_all_tables_from_database(engine)
    print(f"🗄️  Tabelas existentes no banco de dados ({len(db_tables)}):")
    for table in sorted(db_tables):
        print(f"   • {table}")
    print()
    
    # Identificar tabelas não usadas
    unused_tables = db_tables - model_tables
    
    # Remover tabelas do sistema do PostgreSQL
    system_tables = {
        'spatial_ref_sys',  # PostGIS
        'django_migrations',  # Migrações do Django (se houver)
        'django_content_type',  # Django (se houver)
        'django_session',  # Django (se houver)
        'django_admin_log',  # Django (se houver)
    }
    
    unused_tables = unused_tables - system_tables
    
    if unused_tables:
        print("⚠️  TABELAS NÃO USADAS PELO SISTEMA (podem ser removidas):")
        for table in sorted(unused_tables):
            print(f"   ✗ {table}")
        print()
        print(f"Total: {len(unused_tables)} tabela(s) não utilizada(s)")
    else:
        print("✅ Todas as tabelas do banco são utilizadas pelo sistema!")
        print()
    
    # Identificar tabelas faltando no banco
    missing_tables = model_tables - db_tables
    if missing_tables:
        print("⚠️  TABELAS DEFINIDAS NOS MODELOS MAS NÃO EXISTEM NO BANCO:")
        for table in sorted(missing_tables):
            print(f"   ⚠ {table}")
        print()
        print(f"Total: {len(missing_tables)} tabela(s) faltando")
    else:
        print("✅ Todas as tabelas dos modelos existem no banco!")
        print()
    
    # Gerar script SQL para dropar tabelas não usadas
    if unused_tables:
        print("=" * 80)
        print("SCRIPT SQL PARA REMOVER TABELAS NÃO USADAS:")
        print("=" * 80)
        print("-- ATENÇÃO: Execute este script com cuidado!")
        print("-- Faça backup do banco antes de executar!")
        print()
        for table in sorted(unused_tables):
            print(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print()
        print("-- Para executar via Python, use:")
        print("-- python backend/scripts/drop_unused_tables.py")
        print()

if __name__ == "__main__":
    main()

