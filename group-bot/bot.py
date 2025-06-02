import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
from config import Config
from database import Database
from ai_processor import generate_response, analyze_context, is_content_safe
import random
from datetime import datetime
import json
import re
import threading
from queue import Queue

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database(Config.DB_NAME)

chat_contexts = {}
message_queue = Queue(maxsize=100)
processing_lock = threading.Lock()


def message_worker():
    """Фоновый обработчик сообщений"""
    while True:
        update, context_data = message_queue.get()
        try:
            with processing_lock:
                handle_group_message(update, context_data)
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
        finally:
            message_queue.task_done()

for _ in range(3):
    threading.Thread(target=message_worker, daemon=True).start()

def should_respond(chat_id: int) -> bool:
    """Определяет, должен ли бот ответить в этом чате"""
    if chat_id not in chat_contexts:
        return False

    ctx = chat_contexts[chat_id]
    message_count = len(ctx["messages"])

    if message_count < Config.MIN_RESPONSE_LENGTH:
        return False

    return random.random() < Config.RESPONSE_PROBABILITY


async def handle_group_message(update: Update, context: CallbackContext):
    try:
        if update.message.new_chat_members or update.message.left_chat_member:
            return
        if not update.message or not update.message.text:
            return

        if update.message.chat.type not in ["group", "supergroup"]:
            return

        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        chat_title = update.message.chat.title or f"Чат {chat_id}"

        if chat_id not in chat_contexts:
            chat_contexts[chat_id] = {
                "messages": [],
                "participants": set(),
                "last_response": datetime.min
            }

        chat_context = chat_contexts[chat_id]

        clean_text = re.sub(r'^/[\w]+@?[\w]*\s*', '', update.message.text).strip()
        if not clean_text:
            return

        chat_context["messages"].append(clean_text)
        chat_context["participants"].add(user_id)

        if len(chat_context["messages"]) > Config.CONTEXT_SIZE:
            chat_context["messages"] = chat_context["messages"][-Config.CONTEXT_SIZE:]

        bot_response = None
        response_generated = False

        if should_respond(chat_id):
            if is_content_safe("\n".join(chat_context["messages"])):
                bot_response = generate_response(chat_context["messages"])
                if bot_response and len(bot_response) > 1:
                    await update.message.reply_text(bot_response)
                    response_generated = True
                    chat_context["last_response"] = datetime.now()

        analysis = analyze_context(chat_context["messages"])

        interaction_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chat_id": chat_id,
            "chat_title": chat_title,
            "context_messages": chat_context["messages"],
            "detected_topic": analysis["topic"],
            "sentiment": analysis["sentiment"],
            "bot_response": bot_response or "",
            "response_generated": response_generated,
            "participants_count": len(chat_context["participants"])
        }

        db.save_interaction(interaction_data)
        logger.info(f"Сохранено взаимодействие в чате {chat_title}")
        message_queue.put((update, context))
        await asyncio.sleep(0)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)


def main():
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUPS,
            handle_group_message
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()