"""
Script para verificar e corrigir todas as tabelas que precisam de family_id.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine
from sqlalchemy import text

def migrate_table(table_name, column_name="family_id", fk_name=None):
    """Migra uma tabela adicionando family_id se necessário"""
    if fk_name is None:
        fk_name = f"fk_{table_name}_family"
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna existe
            check_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=:table_name AND column_name=:column_name
            """)
            result = conn.execute(check_query, {"table_name": table_name, "column_name": column_name})
            exists = result.fetchone() is not None
            
            if not exists:
                print(f"  [INFO] Adicionando coluna {column_name} em {table_name}...")
                # Adicionar a coluna
                alter_query = text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} INTEGER,
                    ADD CONSTRAINT {fk_name} 
                    FOREIGN KEY ({column_name}) REFERENCES families(id)
                """)
                conn.execute(alter_query)
                conn.commit()
                
                # Criar índice
                index_query = text(f"""
                    CREATE INDEX IF NOT EXISTS ix_{table_name}_{column_name} 
                    ON {table_name}({column_name})
                """)
                conn.execute(index_query)
                conn.commit()
                
                print(f"  [OK] Coluna {column_name} adicionada!")
            else:
                print(f"  [INFO] Coluna {column_name} ja existe.")
            
            # Verificar registros sem family_id
            count_query = text(f"""
                SELECT COUNT(*) 
                FROM {table_name} 
                WHERE {column_name} IS NULL
            """)
            result = conn.execute(count_query)
            count = result.fetchone()[0]
            
            if count > 0:
                print(f"  [INFO] Encontrados {count} registros sem {column_name}.")
                
                # Buscar ID da família padrão
                family_query = text("""
                    SELECT id FROM families WHERE codigo_unico = 'DEFAULT'
                """)
                result = conn.execute(family_query)
                family_row = result.fetchone()
                
                if family_row:
                    default_family_id = family_row[0]
                    # Atualizar registros sem family_id
                    update_query = text(f"""
                        UPDATE {table_name} 
                        SET {column_name} = :family_id 
                        WHERE {column_name} IS NULL
                    """)
                    conn.execute(update_query, {"family_id": default_family_id})
                    conn.commit()
                    print(f"  [OK] {count} registros associados a familia padrao.")
                else:
                    print(f"  [ERRO] Familia padrao nao encontrada!")
            else:
                print(f"  [OK] Todos os registros ja tem {column_name} associado.")
            
            return True
    except Exception as e:
        print(f"  [ERRO] Erro ao migrar {table_name}: {e}")
        return False

def migrate_all_tables():
    """Migra todas as tabelas que precisam de family_id"""
    print("[INICIO] Migrando todas as tabelas...\n")
    
    tables = [
        ("maintenance_equipment", "family_id", "fk_maintenance_equipment_family"),
    ]
    
    success_count = 0
    for table_name, column_name, fk_name in tables:
        print(f"\n[MIGRACAO] {table_name}:")
        if migrate_table(table_name, column_name, fk_name):
            success_count += 1
    
    print(f"\n[RESUMO] {success_count}/{len(tables)} tabelas migradas com sucesso!")
    return success_count == len(tables)

if __name__ == "__main__":
    migrate_all_tables()
    print("\n[FIM] Processo concluido!")

