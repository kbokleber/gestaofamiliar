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

        print("Criando tabela finance_import_category_rule (se não existir)...")
        try:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS finance_import_category_rule (
                        id SERIAL PRIMARY KEY,
                        family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
                        category_id INTEGER NOT NULL REFERENCES finance_category(id) ON DELETE CASCADE,
                        pattern VARCHAR(200) NOT NULL,
                        entry_type VARCHAR(10) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 100,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_by_id INTEGER NOT NULL REFERENCES auth_user(id),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        CONSTRAINT finance_import_category_rule_entry_type_chk
                            CHECK (entry_type IN ('EXPENSE', 'INCOME', 'BOTH'))
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_fin_imp_rule_family_active "
                    "ON finance_import_category_rule (family_id, is_active)"
                )
            )
            conn.commit()
            print("Tabela finance_import_category_rule OK.")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao criar finance_import_category_rule: {e}")

if __name__ == "__main__":
    update_db()
