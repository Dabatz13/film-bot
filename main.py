"""
main.py — Точка входа: запускает весь pipeline
"""

import os
import sys

# Добавляем src/ в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fetcher import fetch_articles
from processor import process_all
from notion_writer import write_all


def main():
    print("=" * 55)
    print("🎬  Film News Bot — старт")
    print("=" * 55)

    # Отладка: показываем какие переменные окружения доступны
    print("\n🔍 Проверка переменных окружения:")
    for key in ["GEMINI_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID"]:
        val = os.environ.get(key)
        print(f"  {key}: {'✅ задан' if val else '❌ не найден'}")

    gemini_key   = os.environ.get("GEMINI_API_KEY")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_db_id = os.environ.get("NOTION_DATABASE_ID")

    if not all([gemini_key, notion_token, notion_db_id]):
        missing = [k for k, v in {
            "GEMINI_API_KEY":    gemini_key,
            "NOTION_TOKEN":      notion_token,
            "NOTION_DATABASE_ID": notion_db_id,
        }.items() if not v]
        print(f"\n❌ Не заданы переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    print("\n✅ Все переменные окружения на месте, запускаем бот...")

    # ── Шаг 1: Собираем новости ───────────────────────────────
    print("\n📡 Шаг 1/3 — Сбор новостей с 8 сайтов...")
    articles = fetch_articles()

    if not articles:
        print("ℹ️  Новых статей нет. Завершаем.")
        return

    MAX_ARTICLES = 10
    if len(articles) > MAX_ARTICLES:
        print(f"ℹ️  Найдено {len(articles)} статей, берём топ-{MAX_ARTICLES} самых свежих.")
        articles = articles[:MAX_ARTICLES]

    # ── Шаг 2: Переводим и адаптируем через Gemini ───────────
    print(f"\n🤖 Шаг 2/3 — Перевод {len(articles)} статей через Gemini...")
    processed = process_all(articles, gemini_key)

    if not processed:
        print("ℹ️  Нечего сохранять. Завершаем.")
        return

    # ── Шаг 3: Сохраняем в Notion ────────────────────────────
    print(f"\n📝 Шаг 3/3 — Сохранение в Notion...")
    saved = write_all(processed, notion_token, notion_db_id)

    print("\n" + "=" * 55)
    print(f"🏁  Готово! Собрано: {len(articles)} | Обработано: {len(processed)} | Сохранено: {saved}")
    print("=" * 55)


if __name__ == "__main__":
    main()
