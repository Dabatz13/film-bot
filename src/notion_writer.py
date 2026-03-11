"""
notion_writer.py — Сохранение обработанных новостей в Notion
"""

import requests
from datetime import datetime, timezone
from typing import Optional
from processor import ProcessedArticle


NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


class NotionWriter:
    def __init__(self, token: str, database_id: str):
        self.db_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _already_exists(self, article_id: str) -> bool:
        """Проверяем дубликат по ArticleID."""
        r = requests.post(
            f"{BASE_URL}/databases/{self.db_id}/query",
            headers=self.headers,
            json={"filter": {"property": "ArticleID", "rich_text": {"equals": article_id}}}
        )
        return len(r.json().get("results", [])) > 0

    def add(self, article: ProcessedArticle) -> bool:
        if self._already_exists(article.id):
            print(f"    ↩️  Уже есть: {article.ru_title[:50]}")
            return False

        full_post = f"{article.ru_title}\n\n{article.ru_text}"
        char_count = len(full_post)

        payload = {
            "parent": {"database_id": self.db_id},
            "properties": {
                "Заголовок": {
                    "title": [{"type": "text", "text": {"content": article.ru_title}}]
                },
                "Статус": {
                    "select": {"name": "На проверке"}
                },
                "Источник": {
                    "select": {"name": article.source}
                },
                "ArticleID": {
                    "rich_text": [{"type": "text", "text": {"content": article.id}}]
                },
                "Оригинал URL": {
                    "url": article.original_url
                },
                "Дата новости": {
                    "date": {"start": article.published_at}
                },
                "Добавлено": {
                    "date": {"start": datetime.now(timezone.utc).isoformat()}
                },
                "Знаков": {
                    "number": char_count
                },
            },
            "children": [
                # Готовый пост — в callout для удобного копирования
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": "Готовый пост для Telegram"}}],
                        "icon": {"emoji": "📋"},
                        "color": "blue_background"
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": full_post}}]
                    }
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Оригинальная статья"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {
                                "content": article.original_title,
                                "link": {"url": article.original_url}
                            }
                        }]
                    }
                },
            ]
        }

        # Обложка страницы — картинка из статьи
        if article.image_url:
            payload["cover"] = {"type": "external", "external": {"url": article.image_url}}

        r = requests.post(f"{BASE_URL}/pages", headers=self.headers, json=payload)

        if r.status_code == 200:
            print(f"    ✅ {article.ru_title[:50]} ({char_count} зн.)")
            return True
        else:
            print(f"    ❌ Ошибка Notion {r.status_code}: {r.text[:150]}")
            return False


def write_all(articles: list[ProcessedArticle], token: str, database_id: str) -> int:
    writer = NotionWriter(token, database_id)
    saved = sum(1 for a in articles if writer.add(a))
    print(f"\n✅ Сохранено в Notion: {saved}/{len(articles)}")
    return saved
