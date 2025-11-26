"""
Script para criar uma família padrão e associar todos os usuários existentes a ela.
Execute este script uma vez para migrar os dados existentes.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.user import User
from app.models.family import Family

def migrate_users_to_family():
    """Cria uma família padrão e associa todos os usuários existentes a ela"""
    db = SessionLocal()
    try:
        # Verificar se já existe uma família padrão
        default_family = db.query(Family).filter(Family.codigo_unico == "DEFAULT").first()
        
        if not default_family:
            # Criar família padrão
            default_family = Family(
                name="Família Padrão",
                codigo_unico="DEFAULT"
            )
            db.add(default_family)
            db.commit()
            db.refresh(default_family)
            print(f"[OK] Familia padrao criada: ID={default_family.id}, Nome={default_family.name}")
        else:
            print(f"[INFO] Familia padrao ja existe: ID={default_family.id}, Nome={default_family.name}")
        
        # Buscar todos os usuários sem família
        users_without_family = db.query(User).filter(User.family_id == None).all()
        
        if users_without_family:
            print(f"\n[INFO] Encontrados {len(users_without_family)} usuarios sem familia:")
            for user in users_without_family:
                print(f"   - {user.username} (ID: {user.id})")
                user.family_id = default_family.id
            
            db.commit()
            print(f"\n[OK] Todos os usuarios foram associados a familia padrao!")
        else:
            print("\n[OK] Todos os usuarios ja estao associados a uma familia.")
        
        # Mostrar estatísticas finais
        total_users = db.query(User).count()
        users_in_default_family = db.query(User).filter(User.family_id == default_family.id).count()
        print(f"\n[STATS] Estatisticas:")
        print(f"   - Total de usuarios: {total_users}")
        print(f"   - Usuarios na familia padrao: {users_in_default_family}")
        
    except Exception as e:
        db.rollback()
        print(f"[ERRO] Erro durante a migracao: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("[INICIO] Iniciando migracao de usuarios para familia padrao...\n")
    migrate_users_to_family()
    print("\n[FIM] Migracao concluida!")

