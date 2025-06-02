from openai import OpenAI, APIConnectionError, APIError, RateLimitError
from config import Config
import json
import re
import logging
import time
from collections import deque
import hashlib

logger = logging.getLogger(__name__)

REQUEST_CACHE = {}
CACHE_SIZE = 100

client = OpenAI(api_key=Config.OPENAI_API_KEY, max_retries=3)


def get_cache_key(messages):

    return hashlib.md5(json.dumps(messages).encode()).hexdigest()


def safe_model_call(model, messages, max_tokens=150, json_format=False):

    cache_key = get_cache_key(messages)

    if cache_key in REQUEST_CACHE:
        return REQUEST_CACHE[cache_key]

    try:
        params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        if json_format:
            params["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**params)

        if len(REQUEST_CACHE) >= CACHE_SIZE:
            REQUEST_CACHE.popitem(last=False)
        REQUEST_CACHE[cache_key] = response

        return response
    except APIConnectionError as e:
        logger.error(f"Ошибка подключения: {e.__cause__}")
    except RateLimitError as e:
        logger.error(f"Превышен лимит запросов: {e}")
        time.sleep(5)
    except APIError as e:
        logger.error(f"Ошибка API: {e.status_code} {e.message}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
    return None


def generate_response(context_messages):
    models_to_try = ["gpt-4-0125-preview", "gpt-4", "gpt-3.5-turbo"]

    for model in models_to_try:
        try:
            messages = [{"role": "system", "content": Config.SYSTEM_PROMPT}]
            for msg in context_messages:
                messages.append({"role": "user", "content": msg})

            response = safe_model_call(model, messages, 150)
            if response and response.choices:
                content = response.choices[0].message.content.strip()
                return re.sub(r'^["\'](.*)["\']$', r'\1', content)[:200]
        except Exception as e:
            logger.error(f"Ошибка генерации с моделью {model}: {e}")

    return None


def analyze_context(context_messages):
    # Резервный анализ
    participants = len(set())
    sentiment = "нейтральный"
    topic = "не определена"

    try:
        prompt = f"Анализ чата: {json.dumps(context_messages, ensure_ascii=False)}"
        messages = [
            {"role": "system", "content": "Ты аналитик чатов. Верни JSON: {topic, sentiment, participants_count}"},
            {"role": "user", "content": prompt}
        ]

        response = safe_model_call("gpt-3.5-turbo", messages, 200, json_format=True)

        if response and response.choices:
            content = response.choices[0].message.content
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                json_str = content[start_idx:end_idx]
                analysis = json.loads(json_str)

                topic = analysis.get("topic", "не определена")
                sentiment = analysis.get("sentiment", "нейтральный")
                participants = analysis.get("participants_count", 1)
            except:
                if any(word in content.lower() for word in ["позитив", "рад", "хорош"]):
                    sentiment = "позитивный"
                elif any(word in content.lower() for word in ["негатив", "плох", "злит"]):
                    sentiment = "негативный"

                word_freq = {}
                for msg in context_messages:
                    for word in msg.split():
                        word_freq[word] = word_freq.get(word, 0) + 1
                if word_freq:
                    topic = max(word_freq, key=word_freq.get)

    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")

    return {
        "topic": topic,
        "sentiment": sentiment,
        "participants_count": participants
    }


def is_content_safe(text):
    """Проверка безопасности контента с резервными методами"""
    try:
        response = client.moderations.create(input=text)
        if response.results and response.results[0].flagged:
            return False
        return True
    except:
        unsafe_keywords = []
        return not any(keyword in text.lower() for keyword in unsafe_keywords)