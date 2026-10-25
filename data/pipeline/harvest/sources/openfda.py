"""FDA CAERS: consumer and doctor reports of harm after food and supplement products, matched by brand name."""
import urllib.parse

from net import get

API = "https://api.fda.gov/food/event.json"
MAX_SKIP = 25000  # openFDA refuses deeper paging


def fetch(substance: dict, limit: int):
    q = urllib.parse.quote(f'products.name_brand:"{substance["en"]}"')
    got = 0
    while got < min(limit, MAX_SKIP):
        data = get(f"{API}?search={q}&limit={min(100, limit - got)}&skip={got}")
        rows = (data or {}).get("results", [])
        for x in rows:
            reactions = x.get("reactions", [])
            yield {
                "source": "openfda", "source_id": x["report_number"], "kind": "safety", "level": "case",
                "title": "; ".join(reactions[:5]), "text": ", ".join(p.get("name_brand", "") for p in x.get("products", [])),
                "url": f"https://api.fda.gov/food/event.json?search=report_number:{x['report_number']}",
                "published": x.get("date_started") or x.get("date_created"), "lang": "en",
                "extra": {"outcomes": x.get("outcomes"), "reactions": reactions, "consumer": x.get("consumer")},
            }
        got += len(rows)
        if len(rows) < 100:
            return
