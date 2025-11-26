"""
Script para criar todas as tabelas no banco de dados.
Execute este script uma vez para criar as tabelas necessárias.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, engine
from app.models import *  # Importar todos os modelos para que sejam registrados

def create_tables():
    """Cria todas as tabelas no banco de dados"""
    print("[INICIO] Criando tabelas no banco de dados...\n")
    
    try:
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        print("[OK] Tabelas criadas com sucesso!")
        
        # Listar tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n[INFO] Tabelas criadas ({len(tables)}):")
        for table in sorted(tables):
            print(f"   - {table}")
        
    except Exception as e:
        print(f"[ERRO] Erro ao criar tabelas: {e}")
        raise

if __name__ == "__main__":
    create_tables()
    print("\n[FIM] Processo concluido!")

