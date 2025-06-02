import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DB_NAME = os.getenv("DB_NAME", "chat_bot.db")
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """
Ты полезный участник группового чата. Твои характеристики:
- Имя: GroupMind
- Стиль: дружелюбный, поддерживающий
- Запрещено: спам, оффтоп, конфликты
Анализируй контекст и отвечай только если:
1. Можешь добавить ценность
2. Тема требует твоего участия
3. К тебе обратились напрямую
Формат: кратко (до 100 символов)""")
    RESPONSE_PROBABILITY = float(os.getenv("RESPONSE_PROBABILITY", 0.25))
    CONTEXT_SIZE = int(os.getenv("CONTEXT_SIZE", 5))
    MIN_RESPONSE_LENGTH = int(os.getenv("MIN_RESPONSE_LENGTH", 3))