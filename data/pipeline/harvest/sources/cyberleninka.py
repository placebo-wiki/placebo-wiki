"""CyberLeninka: Russian-language journals, searched by the Russian name; no publication types, so level is unknown."""
from __future__ import annotations
import ast
import re

from net import get

API = "https://cyberleninka.ru/api/search"


def plain(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(substance: dict, limit: int):
    got = 0
    while got < limit:
        data = get(API, {"mode": "articles", "q": substance["name"], "size": min(100, limit - got), "from": got})
        rows = (data or {}).get("articles", [])
        for x in rows:
            authors = x.get("authors")
            if isinstance(authors, str) and authors.startswith("["):
                authors = ast.literal_eval(authors)
            yield {
                "source": "cyberleninka", "source_id": x["link"], "kind": "science", "level": "unknown",
                "title": plain(x.get("name")), "text": plain(x.get("annotation")), "url": "https://cyberleninka.ru" + x["link"],
                "published": x.get("year"), "authors": ", ".join(authors or []) if isinstance(authors, list) else authors,
                "journal": x.get("journal"), "lang": "ru",
            }
        got += len(rows)
        if not rows:
            return
