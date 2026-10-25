"""Writes the source counts into the stats block of site/index.html (between <!--stats--> and <!--/stats-->).

Numbers: studies collected in data/base/base.sqlite (papers and trial registrations; people's posts and FDA complaints
are not studies and are not counted), sources behind the verdicts in data/catalog.json, substances in the catalog.
Without the base file the block keeps its current numbers.
"""
import json
import pathlib
import re
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
INDEX = ROOT.parent / "site" / "index.html"
BASE = ROOT / "base" / "base.sqlite"
GROUPS = [  # bar segments, strongest first
    ("meta", ("meta",), ("мета-анализ", "мета-анализа", "мета-анализов")),
    ("rct", ("rct",), ("РКИ", "РКИ", "РКИ")),
    ("obs", ("trial", "cohort", "case_control", "cross_sectional", "observational", "case"),
     ("испытание без рандомизации или наблюдение", "испытания без рандомизации и наблюдения", "испытаний без рандомизации и наблюдений")),
    ("other", ("unknown", "animal_cell", "review"),
     ("прочее: опыты на животных, обзоры", "прочих: опыты на животных, обзоры", "прочих: опыты на животных, обзоры")),
]


def plural(n: int, forms: tuple) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    return forms[1] if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else forms[2]


def num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def verdict_sources(items: list) -> int:
    keys = set()
    for it in items:
        # "reviews" on a card are further reading from Europe PMC; the verdict rests on "sources"
        for s in it.get("sources") or []:
            key = s.get("pmid") or (s.get("doi") or "").lower() or (s.get("title") or "").lower()
            if key:
                keys.add(key)
    return len(keys)


def block(studies: dict, sources: int, substances: int) -> str:
    total = sum(studies.values())
    parts = []
    for key, levels, forms in GROUPS:
        n = sum(studies.get(lv, 0) for lv in levels)
        parts.append(f'<span class="st-{key}" style="flex:{n}" data-t="{num(n)} {plural(n, forms)}"></span>')
    return (f'<div class="st" id="stats"><div class="st-big">{num(total)}</div>'
            f'<p class="st-cap">{plural(total, ("исследование собрано", "исследования собраны", "исследований собрано"))}. '
            f'<b>{num(sources)}</b> сильнейших легли в вердикты по <b>{num(substances)}</b> '
            f'{plural(substances, ("БАДу", "БАДам", "БАДам"))}</p>'
            f'<div class="st-bar" role="img" aria-label="Из собранного: '
            + ", ".join(re.search(r'data-t="([^"]+)"', p).group(1) for p in parts)
            + f'">{"".join(parts)}</div><p class="st-leg" id="st-leg">мета-анализы · РКИ · наблюдения · прочее</p></div>')


def main():
    if not BASE.exists():
        print("нет data/base/base.sqlite: цифры на главной не обновлены")
        return
    db = sqlite3.connect(BASE)
    studies = dict(db.execute("select level, count(*) from findings where kind in ('science', 'registry') group by level"))
    items = json.loads((ROOT / "catalog.json").read_text())["items"]
    html = INDEX.read_text()
    new = re.sub(r"<!--stats-->.*?<!--/stats-->", "<!--stats-->" + block(studies, verdict_sources(items), len(items)) + "<!--/stats-->",
                 html, flags=re.S)
    if new == html and "<!--stats-->" not in html:
        raise SystemExit("в site/index.html нет меток <!--stats-->")
    INDEX.write_text(new)
    print(f"главная: {sum(studies.values())} исследований, {verdict_sources(items)} источников вердиктов, {len(items)} БАДов")


if __name__ == "__main__":
    main()
