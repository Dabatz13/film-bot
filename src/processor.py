"""
processor.py — Перевод и адаптация новостей через Google Gemini API (бесплатно)
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


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={api_key}"
)

PROMPT_PREFIX = """Ты — редактор Telegram-канала о кино на русском языке.
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
9. Отвечай ТОЛЬКО валидным JSON без markdown и пояснений

Верни JSON строго в таком формате:
{"ru_title": "Заголовок на русском (до 80 знаков)", "ru_text": "Текст поста на русском (до 900 знаков)"}

Новость с сайта """


def build_prompt(source: str, title: str, summary: str) -> str:
    # Обрезаем summary чтобы не превысить лимит токенов
    clean_summary = summary[:800]
    return PROMPT_PREFIX + source + ":\nЗаголовок: " + title + "\nТекст: " + clean_summary


def call_gemini(api_key: str, prompt: str) -> Optional[str]:
    url = GEMINI_URL.format(api_key=api_key)
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 512},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["candidates"][0]["content"]["parts"][0]["text"]


def process_article(api_key: str, article: RawArticle) -> Optional[ProcessedArticle]:
    prompt = build_prompt(article.source, article.title, article.summary)

    # Повторяем при 429 с нарастающей паузой
    retries = 3
    for attempt in range(retries):
        try:
            raw = call_gemini(api_key, prompt).strip()

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

        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)  # 30с, 60с, 90с
                print(f"  ⏳ Лимит Gemini, жду {wait}с (попытка {attempt+1}/{retries})...")
                time.sleep(wait)
            elif e.code == 400:
                print(f"  ⚠️  Bad Request [{article.title[:50]}] — пропускаем")
                return None
            else:
                print(f"  ⚠️  Gemini ошибка {e.code} [{article.title[:50]}]")
                return None
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON-ошибка [{article.title[:50]}]: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️  Ошибка [{article.title[:50]}]: {e}")
            return None

    print(f"  ❌ Не удалось обработать после {retries} попыток: {article.title[:50]}")
    return None


def process_all(articles: list[RawArticle], api_key: str) -> list[ProcessedArticle]:
    results = []

    for i, article in enumerate(articles, 1):
        print(f"  🤖 [{i}/{len(articles)}] {article.title[:60]}...")
        processed = process_article(api_key, article)
        if processed:
            results.append(processed)
        time.sleep(10.0)  # 10 секунд между запросами — в рамках лимита 15 RPM

    print(f"\n✅ Обработано: {len(results)}/{len(articles)}")
    return results
