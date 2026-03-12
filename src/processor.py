"""
processor.py — Перевод и адаптация новостей через OpenRouter API (бесплатно)
"""

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional
from fetcher import RawArticle


@dataclass
class ProcessedArticle:
    id: str
    source: str
    original_title: str
    original_url: str
    ru_title: str
    ru_text: str
    image_url: Optional[str]
    published_at: str
    status: str = "pending"


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Бесплатная модель — хорошо переводит на русский
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

SYSTEM_PROMPT = """Ты — редактор Telegram-канала о кино на русском языке.
Переводишь и адаптируешь новости с английских кино-сайтов для русскоязычной аудитории.

Правила:
1. Язык живой и разговорный — как будто рассказываешь другу интересную новость
2. Текст поста (без заголовка) — строго до 900 знаков включая пробелы
3. Заголовок — до 80 знаков, конкретный и цепляющий
4. 1-2 эмодзи максимум, только если уместно
5. Без штампов: "захватывающий", "невероятный", "потрясающий" — замени конкретными фактами
6. Имена — в русской транскрипции (Том Хэнкс, Кристофер Нолан и т.д.)
7. Название фильма: оригинал + русский перевод в скобках, если он известен
8. Без ссылок и хэштегов в тексте
9. Отвечай ТОЛЬКО валидным JSON без markdown и пояснений"""


def call_openrouter(api_key: str, system: str, user: str) -> Optional[str]:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/film-news-bot",
            "X-Title": "Film News Bot",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"]


def process_article(api_key: str, article: RawArticle) -> Optional[ProcessedArticle]:
    user_prompt = (
        "Новость с сайта " + article.source + ":\n"
        "Заголовок: " + article.title + "\n"
        "Текст: " + article.summary[:1200] + "\n\n"
        'Верни JSON: {"ru_title": "...", "ru_text": "..."}'
    )

    try:
        raw = call_openrouter(api_key, SYSTEM_PROMPT, user_prompt)
        if not raw:
            return None
        raw = raw.strip()

        # Убираем markdown-обёртки если есть
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    raw = part
                    break

        data = json.loads(raw)
        ru_title = str(data.get("ru_title", article.title)).strip()[:80]
        ru_text  = str(data.get("ru_text", "")).strip()[:900]

        return ProcessedArticle(
            id=article.id,
            source=article.source,
            original_title=article.title,
            original_url=article.url,
            ru_title=ru_title,
            ru_text=ru_text,
            image_url=article.image_url,
            published_at=article.published_at,
        )

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON-ошибка [{article.title[:50]}]: {e}")
        return None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:200]
        print(f"  ⚠️  HTTP-ошибка {e.code} [{article.title[:50]}]: {body}")
        return None
    except Exception as e:
        print(f"  ⚠️  Ошибка [{article.title[:50]}]: {e}")
        return None


def process_all(articles: list[RawArticle], api_key: str) -> list[ProcessedArticle]:
    results = []

    for i, article in enumerate(articles, 1):
        print(f"  🤖 [{i}/{len(articles)}] {article.title[:60]}...")
        processed = process_article(api_key, article)
        if processed:
            results.append(processed)
        time.sleep(3.0)  # Пауза между запросами

    print(f"\n✅ Обработано: {len(results)}/{len(articles)}")
    return results
