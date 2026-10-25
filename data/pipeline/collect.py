"""Collects evidence for a new substance: the most cited meta-analyses and systematic reviews with abstracts from Europe PMC.

python3 collect.py "Спирулина" [english name]  ->  data/drafts/<slug>/evidence.json
"""
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
from nodash import clean  # noqa: E402
from translit import slug  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "drafts"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = {"User-Agent": "placebo.wiki/1.0 (https://placebo.wiki)"}
# a review counts only if it is about taking the substance, not about measuring it or genes named alike
INTAKE = re.compile(r"\b(supplement\w*|intake|administration|dietary|oral|capsule|extract|consumption|treatment|therapy|randomi[sz]ed)\b", re.I)


def get(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def english(name: str) -> str:
    if not re.search(r"[а-яё]", name, re.I):
        return name
    s = get(f"https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=ru&uselang=ru&type=item&limit=1&search={urllib.parse.quote(name)}")
    if not s.get("search"):
        return ""
    qid = s["search"][0]["id"]
    e = get(f"https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels|aliases&languages=en&ids={qid}")["entities"][qid]
    return (e.get("labels", {}).get("en") or {}).get("value", "")


def collect(name: str, en: str = "", per: int = 25) -> dict:
    en = en or english(name)
    if not en:
        raise SystemExit(f"no English name for {name}")
    q = f'TITLE:"{en}" AND (PUB_TYPE:"meta-analysis" OR PUB_TYPE:"systematic-review") AND SRC:MED'
    data = get(f"{EPMC}?query={urllib.parse.quote(q)}&format=json&resultType=core&pageSize={per}&sort={urllib.parse.quote('CITED desc')}")
    rows, dropped = [], 0
    for x in data.get("resultList", {}).get("result", []):
        abstract = re.sub(r"<[^>]+>", " ", x.get("abstractText") or "")
        if not abstract or not INTAKE.search(abstract + " " + (x.get("title") or "")):
            dropped += 1
            continue
        rows.append({"pmid": x.get("pmid"), "doi": x.get("doi"), "title": x.get("title"), "year": x.get("pubYear"),
                     "journal": (x.get("journalInfo") or {}).get("journal", {}).get("title"),
                     "cited_by": x.get("citedByCount"), "abstract": re.sub(r"\s+", " ", abstract).strip()})
    return {"name": name, "name_en": en, "query": q, "hits": data.get("hitCount", 0), "dropped": dropped, "items": rows}


if __name__ == "__main__":
    name = sys.argv[1]
    ev = collect(name, sys.argv[2] if len(sys.argv) > 2 else "")
    out = DRAFTS / slug(name)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence.json").write_text(clean(json.dumps(ev, ensure_ascii=False, indent=1)))
    print(f"{name} ({ev['name_en']}): {len(ev['items'])} обзоров с аннотациями из {ev['hits']}, отсеяно {ev['dropped']}")
