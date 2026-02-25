"""
Script para verificar se as chaves de Telegram e IA estão gravadas no banco.
Não exibe as chaves, apenas se existem (incluídas ou não).
Execute: python -m scripts.check_telegram_ai_keys
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.telegram import FamilyTelegramConfig, FamilyAIConfig
from app.models.family import Family


def main():
    db = SessionLocal()
    try:
        families = db.query(Family).order_by(Family.id).all()
        print("Famílias e status das chaves (Telegram + IA):\n")
        for f in families:
            bot = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == f.id).first()
            ai = db.query(FamilyAIConfig).filter(FamilyAIConfig.family_id == f.id).first()

            token_incluido = bot is not None and bool(bot.bot_token)
            bot_username = (bot.bot_username or "—") if bot else "—"

            openai_incluida = ai is not None and bool(ai.openai_api_key) if ai else False
            azure_incluida = ai is not None and bool(ai.azure_endpoint and ai.azure_api_key) if ai else False

            print(f"  Família id={f.id} | {f.name}")
            print(f"    Token do bot (Telegram): {'INCLUÍDO (oculto)' if token_incluido else 'não incluído'} | @username: {bot_username}")
            print(f"    Chave OpenAI:            {'INCLUÍDA (oculta)' if openai_incluida else 'não incluída'}")
            print(f"    Config Azure:            {'INCLUÍDA (oculta)' if azure_incluida else 'não incluída'}")
            print()
        print("Fim da verificação.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
