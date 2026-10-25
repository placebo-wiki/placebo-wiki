from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "placebo.wiki/1.0 (https://placebo.wiki)"}


class Blocked(Exception):
    """The site refused us (403, 429): access is the owner's job, not a bug in the collector."""


RETRY_WAITS = (5, 30, 120)  # a dropped connection or a 5xx usually passes on a later try


def get(url: str, body: dict | None = None, timeout: int = 60):
    data = json.dumps(body).encode() if body is not None else None
    headers = {**UA, **({"Content-Type": "application/json"} if data else {})}
    for wait in (*RETRY_WAITS, None):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Blocked(f"{e.code} {url.split('?')[0]}") from e
            if e.code == 404:
                return None
            if wait is None or e.code < 500:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if wait is None:
                raise
        time.sleep(wait)
