"""
fetcher.py — Сбор новостей с RSS-лент 8 кино-сайтов
"""

import feedparser
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


RSS_FEEDS = {
    "Deadline":               "https://deadline.com/feed/",
    "Variety":                "https://variety.com/feed/",
    "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Collider":               "https://collider.com/feed/",
    "World of Reel":          "https://www.worldofreel.com/blog?format=rss",
    "IndieWire":              "https://www.indiewire.com/feed/",
    "The Wrap":               "https://www.thewrap.com/feed/",
    "Slash Film":             "https://www.slashfilm.com/feed/",
}

KEYWORDS = [
    "movie", "film", "actor", "actress", "director", "box office",
    "trailer", "premiere", "casting", "sequel", "remake", "series",
    "oscar", "award", "release", "production", "streaming", "netflix",
    "disney", "marvel", "cinema", "screenplay", "review", "festival",
    "sundance", "cannes", "biopic", "reboot", "animated", "documentary",
]

SEEN_IDS_FILE = Path("data/seen_ids.json")


@dataclass
class RawArticle:
    id: str
    source: str
    title: str
    url: str
    summary: str
    image_url: Optional[str]
    published_at: str


def load_seen_ids() -> set:
    if SEEN_IDS_FILE.exists():
        with open(SEEN_IDS_FILE, "r") as f:
            return set(json.load(f).get("ids", []))
    return set()


def save_seen_ids(ids: set):
    SEEN_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump({"ids": list(ids)}, f, indent=2)


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def extract_image(entry) -> Optional[str]:
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            if m.get("medium") == "image" or m.get("type", "").startswith("image"):
                return m.get("url")
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("href") or enc.get("url")
    summary = getattr(entry, "summary", "") or ""
    if 'src="' in summary:
        start = summary.find('src="') + 5
        end = summary.find('"', start)
        src = summary[start:end]
        if src.startswith("http") and any(e in src for e in [".jpg", ".jpeg", ".png", ".webp"]):
            return src
    return None


def is_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)


def fetch_articles() -> list[RawArticle]:
    seen_ids = load_seen_ids()
    new_articles = []

    for source, feed_url in RSS_FEEDS.items():
        print(f"  📡 {source}...")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                url = entry.get("link", "")
                if not url:
                    continue
                article_id = make_id(url)
                if article_id in seen_ids:
                    continue

                title = entry.get("title", "").strip()
                summary = (entry.get("summary") or entry.get("description") or "")[:2000]

                if not is_relevant(title, summary):
                    continue

                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                published_at = (
                    datetime(*pub[:6], tzinfo=timezone.utc).isoformat()
                    if pub else datetime.now(timezone.utc).isoformat()
                )

                new_articles.append(RawArticle(
                    id=article_id,
                    source=source,
                    title=title,
                    url=url,
                    summary=summary,
                    image_url=extract_image(entry),
                    published_at=published_at,
                ))
                seen_ids.add(article_id)

        except Exception as e:
            print(f"  ⚠️  Ошибка {source}: {e}")
        time.sleep(0.5)

    save_seen_ids(seen_ids)
    print(f"\n✅ Новых статей: {len(new_articles)}")
    return new_articles
