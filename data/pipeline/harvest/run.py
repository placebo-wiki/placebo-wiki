"""Collects everything found about each substance from every source into data/base/base.sqlite.

python3 run.py                          all substances, all sources, 100 per source
python3 run.py --only kreatin,magnij    selected substances (ids from data/catalog.json)
python3 run.py --sources europepmc --limit 1000
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import base  # noqa: E402
import levels  # noqa: E402
import names  # noqa: E402
from net import Blocked  # noqa: E402
from notify import alert  # noqa: E402
from sources import ALL  # noqa: E402
from sources.stubs import Stub  # noqa: E402

CATALOG = pathlib.Path(__file__).resolve().parents[2] / "catalog.json"


def substances(only: set) -> list[dict]:
    en = names.load()
    return [{"id": x["id"], "name": x["name"], "en": en.get(x["id"], [""])[0], "names": en.get(x["id"], [])}
            for x in json.loads(CATALOG.read_text())["items"] if not only or x["id"] in only]


def relevel(r: dict) -> None:
    lv = levels.guess(r.get("title"), r.get("text")) if r["level"] == "unknown" else None
    if lv:
        r["level"] = lv
        r["extra"] = {**(r.get("extra") or {}), "level_by": "keywords"}


def relevel_base(db) -> int:
    """Applies the keyword rules to findings stored before they existed."""
    n = 0
    for fid, title, text, extra in db.execute("select id, title, text, extra from findings where level = 'unknown'").fetchall():
        r = {"level": "unknown", "title": title, "text": text, "extra": json.loads(extra or "{}")}
        relevel(r)
        if r["level"] != "unknown":
            db.execute("update findings set level = ?, extra = ? where id = ?", (r["level"], json.dumps(r["extra"], ensure_ascii=False), fid))
            n += 1
    db.commit()
    return n


def merge(db, path: str) -> tuple[int, int]:
    """Moves findings from another base file (a parallel run) into this one with the usual dedupe."""
    src = base.connect(path)
    cols = ["source", "source_id", "kind", "level", "substance", "title", "text", "url", "published", "authors", "journal",
            "doi", "pmid", "lang", "extra"]
    added = skipped = 0
    for row in src.execute(f"select {', '.join(cols)} from findings"):
        r = dict(zip(cols, row))
        r["extra"] = json.loads(r["extra"] or "{}")
        if base.add(db, r.pop("substance"), r):
            added += 1
        else:
            skipped += 1
    db.commit()
    return added, skipped


def harvest(db, sub: dict, name: str, limit: int) -> tuple[str, int, int, str]:
    if not sub["en"] and name != "cyberleninka":
        return "no_name", 0, 0, "нет английского названия в aliases"
    added = skipped = 0
    try:
        for r in ALL[name](sub, limit):
            relevel(r)
            if base.add(db, sub["id"], r):
                added += 1
            else:
                skipped += 1
    except Stub as e:
        return "stub", 0, 0, str(e)
    except Blocked as e:
        return "blocked", added, skipped, str(e)
    except Exception as e:  # one broken site must not stop the others
        return "error", added, skipped, f"{type(e).__name__}: {e}"
    return "ok", added, skipped, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--sources", default=",".join(ALL))
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--db", default=str(base.DB))
    ap.add_argument("--relevel", action="store_true", help="only re-level stored findings by keywords")
    ap.add_argument("--merge", default="", help="only move findings from another base file into this one")
    a = ap.parse_args()
    db = base.connect(a.db)
    if a.merge:
        added, skipped = merge(db, a.merge)
        print(f"перенесено {added}, уже были {skipped}")
        return
    if a.relevel:
        print(f"уровень определён по словам у {relevel_base(db)} находок")
        return
    subs, srcs = substances({s for s in a.only.split(",") if s}), [s for s in a.sources.split(",") if s]
    totals, stubs, problems = {n: [0, 0] for n in srcs}, {}, {}
    for sub in subs:
        for name in srcs:
            started = base.now()
            status, added, skipped, err = harvest(db, sub, name, a.limit)
            db.execute("insert into runs (source, substance, started, finished, added, skipped, status, error) values (?,?,?,?,?,?,?,?)",
                       (name, sub["id"], started, base.now(), added, skipped, status, err))
            db.commit()
            totals[name][0] += added
            totals[name][1] += skipped
            if status == "stub":
                stubs[name] = err
            elif status != "ok":
                problems.setdefault((name, status, err.split(":")[0]), []).append(sub["id"])
    for name, (added, skipped) in totals.items():
        print(f"{name:15} заглушка: {stubs[name]}" if name in stubs else f"{name:15} {added} новых, {skipped} уже были")
    if problems:
        text = "Сбор базы: сбои\n" + "\n".join(f"{n} ({s}, {e}): {', '.join(ids[:10])}{' и ещё ' + str(len(ids) - 10) if len(ids) > 10 else ''}"
                                               for (n, s, e), ids in problems.items())
        print(text)
        alert(text)


if __name__ == "__main__":
    main()
