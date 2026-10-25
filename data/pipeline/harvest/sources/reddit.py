"""Reddit through the Arctic Shift archive: reddit.com itself answers 403/429 to scripts, the archive does not.

The archive searches only inside named subreddits, so the collector walks a fixed list of supplement communities.
"""
import time
import urllib.error
import urllib.parse

from net import get

API = "https://arctic-shift.photon-reddit.com/api/posts/search"
SUBREDDITS = ["Supplements", "Nootropics", "Biohackers"]
PAUSE = 1.0
RETRIES = (5, 20, 60)


def ask(url: str):
    # heavy title searches time out on the archive side (HTTP 422 "Timeout. Maybe slow down a bit"); a later retry usually passes
    for wait in (*RETRIES, None):
        try:
            data = get(url)
            time.sleep(PAUSE)
            return data
        except urllib.error.HTTPError as e:
            if wait is None or e.code not in (422, 500, 502, 503, 504):
                raise
            time.sleep(wait)


def fetch(substance: dict, limit: int):
    per = max(1, limit // len(SUBREDDITS))
    for sub in SUBREDDITS:
        before, got = None, 0
        while got < per:
            url = f"{API}?subreddit={sub}&title={urllib.parse.quote(substance['en'])}&limit={min(100, per - got)}"
            data = ask(url + (f"&before={before}" if before else ""))
            if (data or {}).get("error"):
                raise RuntimeError(data["error"])
            rows = (data or {}).get("data") or []
            for x in rows:
                yield {
                    "source": "reddit", "source_id": x["id"], "kind": "people", "level": "people",
                    "title": x.get("title"), "text": x.get("selftext"), "url": "https://www.reddit.com" + x.get("permalink", ""),
                    "published": time.strftime("%Y-%m-%d", time.gmtime(x.get("created_utc") or 0)), "authors": x.get("author"),
                    "journal": "r/" + sub, "lang": "en", "extra": {"score": x.get("score"), "comments": x.get("num_comments")},
                }
            got += len(rows)
            if len(rows) < min(100, per - got + len(rows)):
                break
            before = rows[-1].get("created_utc")
