import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def update_recurrence_schema():
    print("Conectando ao banco de dados...")
    with engine.connect() as conn:
        print("Adicionando colunas start_date e end_date à tabela finance_recurrence...")
        try:
            conn.execute(text("ALTER TABLE finance_recurrence ADD COLUMN IF NOT EXISTS start_date DATE"))
            conn.execute(text("ALTER TABLE finance_recurrence ADD COLUMN IF NOT EXISTS end_date DATE"))
            conn.commit()
            print("Colunas adicionadas com sucesso!")
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar BD: {e}")

if __name__ == "__main__":
    update_recurrence_schema()
