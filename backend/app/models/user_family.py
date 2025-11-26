from sqlalchemy import Column, Integer, ForeignKey, Table
from app.db.base import Base

# Tabela de associação many-to-many entre User e Family
user_families = Table(
    'user_families',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('auth_user.id'), primary_key=True),
    Column('family_id', Integer, ForeignKey('families.id'), primary_key=True)
)

