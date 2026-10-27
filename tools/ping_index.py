"""Tells search engines about the fresh sitemap URLs via IndexNow (Yandex and Bing).

Runs at the end of tools/deploy.sh. The key file site/<KEY>.txt must already be up.
"""
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = "ceeae611d163c783489f7fac3f9c7c7c"
HOST = "placebo.wiki"
ENDPOINTS = ["https://api.indexnow.org/indexnow", "https://yandex.com/indexnow"]


def main() -> None:
    urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "site" / "sitemap.xml").read_text())
    body = json.dumps({"host": HOST, "key": KEY,
                       "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
    for ep in ENDPOINTS:
        req = urllib.request.Request(ep, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"{ep}: {r.status} ({len(urls)} urls)")
        except Exception as e:
            print(f"{ep}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
