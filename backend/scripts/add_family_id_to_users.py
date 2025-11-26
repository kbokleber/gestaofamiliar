"""
Script para adicionar a coluna family_id na tabela auth_user.
Execute este script uma vez para adicionar a coluna.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine
from sqlalchemy import text

def add_family_id_column():
    """Adiciona a coluna family_id na tabela auth_user"""
    print("[INICIO] Adicionando coluna family_id na tabela auth_user...\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='auth_user' AND column_name='family_id'
            """)
            result = conn.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                print("[INFO] Coluna family_id ja existe na tabela auth_user.")
            else:
                # Adicionar a coluna
                alter_query = text("""
                    ALTER TABLE auth_user 
                    ADD COLUMN family_id INTEGER,
                    ADD CONSTRAINT fk_auth_user_family 
                    FOREIGN KEY (family_id) REFERENCES families(id)
                """)
                conn.execute(alter_query)
                conn.commit()
                
                # Criar índice
                index_query = text("""
                    CREATE INDEX IF NOT EXISTS ix_auth_user_family_id 
                    ON auth_user(family_id)
                """)
                conn.execute(index_query)
                conn.commit()
                
                print("[OK] Coluna family_id adicionada com sucesso!")
        
    except Exception as e:
        print(f"[ERRO] Erro ao adicionar coluna: {e}")
        raise

if __name__ == "__main__":
    add_family_id_column()
    print("\n[FIM] Processo concluido!")

