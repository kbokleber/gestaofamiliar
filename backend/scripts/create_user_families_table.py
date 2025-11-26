"""
Script para criar a tabela user_families (relacionamento many-to-many).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine
from sqlalchemy import text

def create_user_families_table():
    """Cria a tabela user_families se não existir"""
    print("[INICIO] Criando tabela user_families...\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a tabela já existe
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
                print("[INFO] Criando tabela user_families...")
                # Criar a tabela
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
                
                # Criar índices
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
                
                print("[OK] Tabela user_families criada com sucesso!")
        
    except Exception as e:
        print(f"[ERRO] Erro ao criar tabela: {e}")
        raise

if __name__ == "__main__":
    create_user_families_table()
    print("\n[FIM] Processo concluido!")

