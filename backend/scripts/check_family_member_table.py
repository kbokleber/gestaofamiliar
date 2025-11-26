"""
Script para verificar e corrigir a tabela healthcare_familymember.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine
from sqlalchemy import text

def check_and_fix_family_member_table():
    """Verifica e corrige a tabela healthcare_familymember"""
    print("[INICIO] Verificando tabela healthcare_familymember...\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna family_id existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='healthcare_familymember' AND column_name='family_id'
            """)
            result = conn.execute(check_query)
            exists = result.fetchone() is not None
            
            if not exists:
                print("[INFO] Coluna family_id nao existe. Adicionando...")
                # Adicionar a coluna
                alter_query = text("""
                    ALTER TABLE healthcare_familymember 
                    ADD COLUMN family_id INTEGER,
                    ADD CONSTRAINT fk_healthcare_familymember_family 
                    FOREIGN KEY (family_id) REFERENCES families(id)
                """)
                conn.execute(alter_query)
                conn.commit()
                
                # Criar índice
                index_query = text("""
                    CREATE INDEX IF NOT EXISTS ix_healthcare_familymember_family_id 
                    ON healthcare_familymember(family_id)
                """)
                conn.execute(index_query)
                conn.commit()
                
                print("[OK] Coluna family_id adicionada!")
            else:
                print("[INFO] Coluna family_id ja existe.")
            
            # Verificar membros sem family_id
            count_query = text("""
                SELECT COUNT(*) 
                FROM healthcare_familymember 
                WHERE family_id IS NULL
            """)
            result = conn.execute(count_query)
            count = result.fetchone()[0]
            
            if count > 0:
                print(f"[INFO] Encontrados {count} membros sem family_id.")
                print("[INFO] Associando a familia padrao...")
                
                # Buscar ID da família padrão
                family_query = text("""
                    SELECT id FROM families WHERE codigo_unico = 'DEFAULT'
                """)
                result = conn.execute(family_query)
                family_row = result.fetchone()
                
                if family_row:
                    default_family_id = family_row[0]
                    # Atualizar membros sem family_id
                    update_query = text("""
                        UPDATE healthcare_familymember 
                        SET family_id = :family_id 
                        WHERE family_id IS NULL
                    """)
                    conn.execute(update_query, {"family_id": default_family_id})
                    conn.commit()
                    print(f"[OK] {count} membros associados a familia padrao (ID: {default_family_id})")
                else:
                    print("[ERRO] Familia padrao nao encontrada!")
            else:
                print("[OK] Todos os membros ja tem family_id associado.")
            
            # Estatísticas
            stats_query = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT family_id) as familias
                FROM healthcare_familymember
            """)
            result = conn.execute(stats_query)
            stats = result.fetchone()
            print(f"\n[STATS] Total de membros: {stats[0]}, Familias: {stats[1]}")
        
    except Exception as e:
        print(f"[ERRO] Erro: {e}")
        raise

if __name__ == "__main__":
    check_and_fix_family_member_table()
    print("\n[FIM] Processo concluido!")

