"""Shared store of everything collected: one SQLite file, one row per finding."""
import json
import pathlib
import sqlite3
import time

DB = pathlib.Path(__file__).resolve().parents[2] / "base" / "base.sqlite"

# level -> (label on the evidence scheme, zone); zones: cause, link, hypothesis
LEVELS = {
    "meta": ("Мета-анализ, систематический обзор", "cause"),
    "rct": ("РКИ", "cause"),
    "trial": ("Испытание без рандомизации", "link"),
    "cohort": ("Когортное", "link"),
    "case_control": ("Случай-контроль", "link"),
    "cross_sectional": ("Поперечное", "link"),
    "observational": ("Наблюдательное", "link"),
    "case": ("Описание случаев", "hypothesis"),
    "animal_cell": ("Животные, клетки", "hypothesis"),
    "review": ("Нарративный обзор", "hypothesis"),
    "people": ("Опыт людей", "hypothesis"),
    "unknown": ("Не определено", None),
}
KINDS = {"science", "registry", "safety", "people"}

SCHEMA = """
create table if not exists findings (
  id integer primary key,
  source text not null,
  source_id text not null,
  kind text not null,
  level text not null,
  substance text not null,
  title text,
  text text,
  url text,
  published text,
  authors text,
  journal text,
  doi text,
  pmid text,
  lang text,
  extra text,
  also_in text,
  fetched_at text not null,
  unique (source, source_id, substance)
);
create index if not exists findings_doi on findings (doi);
create index if not exists findings_pmid on findings (pmid);
create table if not exists runs (
  id integer primary key,
  source text, substance text, started text, finished text,
  added integer, skipped integer, status text, error text
);
"""


def connect(path=DB) -> sqlite3.Connection:
    if str(path) != ":memory:":
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def add(db: sqlite3.Connection, substance: str, r: dict) -> bool:
    """Stores one finding; returns False when it is already in the base under any source."""
    assert r["kind"] in KINDS and r["level"] in LEVELS, r
    # the same paper reaches us from several sources: keep the first row, remember the others
    for key in ("doi", "pmid"):
        if r.get(key):
            row = db.execute(f"select id, source, also_in from findings where {key} = ? and substance = ?", (r[key], substance)).fetchone()
            if row:
                if row[1] != r["source"]:
                    seen = set(json.loads(row[2] or "[]")) | {r["source"]}
                    db.execute("update findings set also_in = ? where id = ?", (json.dumps(sorted(seen)), row[0]))
                return False
    cur = db.execute(
        "insert or ignore into findings (source, source_id, kind, level, substance, title, text, url, published, authors,"
        " journal, doi, pmid, lang, extra, fetched_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (r["source"], str(r["source_id"]), r["kind"], r["level"], substance, r.get("title"), r.get("text"), r.get("url"),
         r.get("published"), r.get("authors"), r.get("journal"), r.get("doi"), r.get("pmid"), r.get("lang"),
         json.dumps(r.get("extra") or {}, ensure_ascii=False), now()))
    return cur.rowcount == 1
