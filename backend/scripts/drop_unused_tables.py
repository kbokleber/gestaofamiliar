"""
Script para dropar tabelas não utilizadas pelo sistema
ATENÇÃO: Execute com cuidado! Faça backup antes!
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
    import sys
    import os
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
    print("REMOVER TABELAS NÃO UTILIZADAS")
    print("=" * 80)
    print()
    
    # Obter tabelas dos modelos
    model_tables = get_all_tables_from_models()
    
    # Obter tabelas do banco
    db_tables = get_all_tables_from_database(engine)
    
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
    
    if not unused_tables:
        print("✅ Não há tabelas não utilizadas para remover!")
        return
    
    print(f"⚠️  TABELAS QUE SERÃO REMOVIDAS ({len(unused_tables)}):")
    for table in sorted(unused_tables):
        print(f"   ✗ {table}")
    print()
    
    # Confirmar
    response = input("Deseja realmente remover essas tabelas? (digite 'SIM' para confirmar): ")
    if response != 'SIM':
        print("Operação cancelada.")
        return
    
    # Dropar tabelas
    print()
    print("Removendo tabelas...")
    with engine.connect() as conn:
        for table in sorted(unused_tables):
            try:
                print(f"   Removendo {table}...", end=" ")
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                conn.commit()
                print("✓")
            except Exception as e:
                print(f"✗ Erro: {e}")
                conn.rollback()
    
    print()
    print("✅ Concluído!")

if __name__ == "__main__":
    main()

