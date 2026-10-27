"""Writes the source counts into the stats block of site/index.html (between <!--stats--> and <!--/stats-->).

Numbers: studies collected in data/base/base.sqlite (papers and trial registrations; people's posts and FDA complaints
are not studies and are not counted), sources behind the verdicts in data/catalog.json, substances in the catalog.
Without the base file the block keeps its current numbers.
Also writes site/b/ev/<id>.json: one number per study for the evidence field on each card (ev.js).
"""
import json
import pathlib
import re
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
INDEX = ROOT.parent / "site" / "index.html"
FIELDS = ROOT.parent / "site" / "b" / "ev"
Y0, Y1 = 1990, 2026  # the field shows these years; counts in the caption cover all years
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
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


def write_fields(db, items: list) -> None:
    """Each study is packed as (year - Y0) * 16 + group * 4 + citation bucket; the bucket is the order of magnitude of cited_by, capped at 3."""
    group = {lv: i for i, (_, levels, _) in enumerate(GROUPS) for lv in levels}
    FIELDS.mkdir(parents=True, exist_ok=True)
    for it in items:
        dots, n = [], [0] * len(GROUPS)
        for level, pub, extra in db.execute(
                "select level, published, extra from findings where substance = ? and kind in ('science', 'registry')", (it["id"],)):
            g = group.get(level, len(GROUPS) - 1)
            n[g] += 1
            y = (pub or "")[:4]
            if not y.isdigit() or not Y0 <= int(y) <= Y1:
                continue
            cited = 0
            if extra:
                try:
                    cited = json.loads(extra).get("cited_by") or 0
                except ValueError:
                    pass
            dots.append((int(y) - Y0) * 16 + g * 4 + min(3, len(str(cited)) - 1 if cited else 0))
        (FIELDS / f"{it['id']}.json").write_text(json.dumps({"y0": Y0, "y1": Y1, "n": n, "d": dots}, separators=(",", ":")))


def live_line(db) -> str:
    last = db.execute("select max(fetched_at) from findings").fetchone()[0] or ""
    fresh = db.execute(f"select count(*) from findings where kind in ('science', 'registry') and published like '{Y1}%'").fetchone()[0]
    when = f"{int(last[8:10])} {MONTHS[int(last[5:7]) - 1]}" if len(last) >= 10 else ""
    return (f'<p class="st-live"><i></i>Обновлено {when} · +{num(fresh)} {plural(fresh, ("новое", "новых", "новых"))} за {Y1} год</p>'
            if when else "")


def block(studies: dict, sources: int, substances: int, live: str = "") -> str:
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
            + f'">{"".join(parts)}</div><p class="st-leg" id="st-leg">мета-анализы · РКИ · наблюдения · прочее</p>{live}</div>')


def main():
    if not BASE.exists():
        print("нет data/base/base.sqlite: цифры на главной не обновлены")
        return
    db = sqlite3.connect(BASE)
    studies = dict(db.execute("select level, count(*) from findings where kind in ('science', 'registry') group by level"))
    items = json.loads((ROOT / "catalog.json").read_text())["items"]
    html = INDEX.read_text()
    new = re.sub(r"<!--stats-->.*?<!--/stats-->", "<!--stats-->" + block(studies, verdict_sources(items), len(items), live_line(db)) + "<!--/stats-->",
                 html, flags=re.S)
    if new == html and "<!--stats-->" not in html:
        raise SystemExit("в site/index.html нет меток <!--stats-->")
    INDEX.write_text(new)
    write_fields(db, items)
    print(f"главная: {sum(studies.values())} исследований, {verdict_sources(items)} источников вердиктов, {len(items)} БАДов")


if __name__ == "__main__":
    main()
