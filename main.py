"""
main.py — Точка входа: запускает весь pipeline
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fetcher import fetch_articles
from processor import process_all
from notion_writer import write_all


def main():
    print("=" * 55)
    print("🎬  Film News Bot — старт")
    print("=" * 55)

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    notion_token   = os.environ.get("NOTION_TOKEN")
    notion_db_id   = os.environ.get("NOTION_DATABASE_ID")

    print("\n🔍 Проверка переменных окружения:")
    for key, val in [("OPENROUTER_API_KEY", openrouter_key), ("NOTION_TOKEN", notion_token), ("NOTION_DATABASE_ID", notion_db_id)]:
        print(f"  {key}: {'✅ задан' if val else '❌ не найден'}")

    if not all([openrouter_key, notion_token, notion_db_id]):
        missing = [k for k, v in {
            "OPENROUTER_API_KEY":  openrouter_key,
            "NOTION_TOKEN":        notion_token,
            "NOTION_DATABASE_ID":  notion_db_id,
        }.items() if not v]
        print(f"\n❌ Не заданы переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    print("\n✅ Все переменные на месте, запускаем...\n")

    # Шаг 1: Сбор новостей
    print("📡 Шаг 1/3 — Сбор новостей с 8 сайтов...")
    articles = fetch_articles()

    if not articles:
        print("ℹ️  Новых статей нет. Завершаем.")
        return

    MAX_ARTICLES = 10
    if len(articles) > MAX_ARTICLES:
        print(f"ℹ️  Найдено {len(articles)} статей, берём топ-{MAX_ARTICLES} самых свежих.")
        articles = articles[:MAX_ARTICLES]

    # Шаг 2: Перевод через OpenRouter
    print(f"\n🤖 Шаг 2/3 — Перевод {len(articles)} статей через OpenRouter...")
    processed = process_all(articles, openrouter_key)

    if not processed:
        print("ℹ️  Нечего сохранять. Завершаем.")
        return

    # Шаг 3: Сохранение в Notion
    print(f"\n📝 Шаг 3/3 — Сохранение в Notion...")
    saved = write_all(processed, notion_token, notion_db_id)

    print("\n" + "=" * 55)
    print(f"🏁  Готово! Собрано: {len(articles)} | Обработано: {len(processed)} | Сохранено: {saved}")
    print("=" * 55)


if __name__ == "__main__":
    main()
