"""
Script para criar usuário administrador
Execute: python create_admin.py
"""
from app.db.base import SessionLocal
from app.models.user import User, Profile
from app.core.security import get_password_hash

def create_admin():
    db = SessionLocal()
    
    try:
        # Verificar se já existe
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("❌ Usuário 'admin' já existe!")
            return
        
        # Criar admin
        admin = User(
            username="admin",
            email="admin@sistemafamiliar.com",
            password=get_password_hash("admin123"),
            first_name="Admin",
            last_name="Sistema",
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        # Criar perfil
        profile = Profile(user_id=admin.id)
        db.add(profile)
        db.commit()
        
        print("✅ Usuário administrador criado com sucesso!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Email: admin@sistemafamiliar.com")
        print("")
        print("⚠️  ATENÇÃO: Mude a senha após o primeiro login!")
        
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

