import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL não encontrada no .env")
    exit(1)

engine = create_engine(DATABASE_URL)

def update_db():
    print(f"Conectando ao banco de dados...")
    with engine.connect() as conn:
        print("Adicionando coluna created_by_id à tabela finance_category...")
        try:
            # 1. Adicionar como nullable primeiro para não dar erro em linhas existentes
            conn.execute(text("ALTER TABLE finance_category ADD COLUMN IF NOT EXISTS created_by_id INTEGER REFERENCES auth_user(id)"))
            
            # 2. Tentar encontrar um usuário admin para preencher os existentes
            admin_id_query = text("SELECT id FROM auth_user ORDER BY id LIMIT 1")
            admin_id_res = conn.execute(admin_id_query).fetchone()
            
            if admin_id_res:
                admin_id = admin_id_res[0]
                print(f"Preenchendo registros existentes com user_id: {admin_id}")
                conn.execute(text(f"UPDATE finance_category SET created_by_id = {admin_id} WHERE created_by_id IS NULL"))
            
            # 3. Tornar non-nullable (opcional, mas condizente com o modelo)
            # conn.execute(text("ALTER TABLE finance_category ALTER COLUMN created_by_id SET NOT NULL"))
            
            conn.commit()
            print("Coluna adicionada e preenchida com sucesso!")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar BD: {e}")

if __name__ == "__main__":
    update_db()
