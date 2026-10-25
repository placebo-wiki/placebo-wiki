"""Exports the shared base as open data: Parquet files for the Hugging Face dataset.

Every finding keeps its description and link; full text only where redistribution is allowed:
ClinicalTrials.gov and openFDA (US government, public domain) and open-access Europe PMC articles.
Abstracts of paywalled articles belong to publishers; CyberLeninka licenses differ per article;
Reddit posts belong to their authors, so only the link, date and community are kept.

uv run --with pyarrow python3 export.py [out_dir]
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import base  # noqa: E402
import names  # noqa: E402

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else base.DB.parent / "export"
CATALOG = pathlib.Path(__file__).resolve().parents[2] / "catalog.json"
TEXT_LICENSE = {"clinicaltrials": "public domain (US government)", "openfda": "public domain (US government)"}


def text_license(source: str, extra: dict) -> str | None:
    if source in TEXT_LICENSE:
        return TEXT_LICENSE[source]
    if source == "europepmc" and extra.get("open_access"):
        return "open access, see the article license"
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(base.DB)
    cols = ["id", "source", "source_id", "kind", "level", "substance", "title", "text", "url", "published", "authors",
            "journal", "doi", "pmid", "lang", "extra", "also_in", "fetched_at"]
    rows = {k: [] for k in ["id", "source", "source_id", "kind", "level", "level_label", "zone", "substance", "title", "text",
                            "text_license", "url", "published", "authors", "journal", "doi", "pmid", "lang", "cited_by",
                            "retracted", "about_intake", "level_by_keywords", "also_in", "fetched_at"]}
    for row in db.execute(f"select {', '.join(cols)} from findings order by id"):
        r = dict(zip(cols, row))
        extra = json.loads(r["extra"] or "{}")
        lic = text_license(r["source"], extra)
        people = r["kind"] == "people"
        out = {
            **{k: r[k] for k in ("id", "source", "source_id", "kind", "level", "substance", "url", "published", "doi", "pmid",
                                 "lang", "fetched_at")},
            "level_label": base.LEVELS[r["level"]][0], "zone": base.LEVELS[r["level"]][1],
            "title": None if people else r["title"], "text": r["text"] if lic else None, "text_license": lic,
            "authors": None if people else r["authors"], "journal": r["journal"],
            "cited_by": extra.get("cited_by"), "retracted": extra.get("retracted"), "about_intake": extra.get("intake"),
            "level_by_keywords": extra.get("level_by") == "keywords", "also_in": json.loads(r["also_in"] or "[]"),
        }
        for k in rows:
            rows[k].append(out[k])
    pq.write_table(pa.table(rows), OUT / "findings.parquet", compression="zstd")
    en = names.load()
    items = json.loads(CATALOG.read_text())["items"]
    pq.write_table(pa.table({"id": [x["id"] for x in items], "name_ru": [x["name"] for x in items],
                             "names_en": [en.get(x["id"], []) for x in items], "verdict": [x.get("verdict") for x in items]}),
                   OUT / "substances.parquet", compression="zstd")
    n = len(rows["id"])
    with_text = sum(1 for t in rows["text"] if t)
    (OUT / "README.md").write_text(card(rows, len(items)))
    print(f"{n} находок, текст у {with_text}, файлы в {OUT}")


def table(counter: dict, head: tuple) -> str:
    lines = [f"| {head[0]} | {head[1]} |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |".replace(f"{v:,}", f"{v:,}".replace(",", " ")) for k, v in sorted(counter.items(), key=lambda kv: -kv[1])]
    return "\n".join(lines)


def card(rows: dict, substances: int) -> str:
    from collections import Counter
    n = len(rows["id"])
    by_source = Counter(rows["source"])
    by_level = Counter(f'{lv} ({lab})' for lv, lab in zip(rows["level"], rows["level_label"]))
    with_text = sum(1 for t in rows["text"] if t)
    date = max(rows["fetched_at"])[:10]
    return CARD.format(n=f"{n:,}".replace(",", " "), substances=substances, date=date, with_text=f"{with_text:,}".replace(",", " "),
                       sources=table(by_source, ("source", "findings")), levels=table(by_level, ("level", "findings")))


CARD = """---
license: other
license_name: mixed-per-source
language:
- en
- ru
pretty_name: placebo.wiki studies on dietary supplements
tags:
- dietary-supplements
- evidence-based-medicine
- pubmed
- clinical-trials
- adverse-events
size_categories:
- 100K<n<1M
configs:
- config_name: findings
  data_files: findings.parquet
  default: true
- config_name: substances
  data_files: substances.parquet
---

# placebo.wiki: studies on dietary supplements

{n} findings about {substances} dietary supplements, collected automatically from open sources and labelled with an
evidence level (meta-analysis, RCT, cohort, case report, animal study...). Collected {date}. Built for
[placebo.wiki](https://placebo.wiki), a Russian-language site that checks whether supplements work better than placebo.

Открытая база placebo.wiki: исследования о БАДах из открытых источников с уровнем доказательности. Собрана автоматически,
людьми не прочитана: вердикты на сайте стоят только на отобранных сильнейших работах.

## Sources

{sources}

- europepmc: Europe PMC (PubMed and European sources); all meta-analyses and RCTs plus the most cited other papers per substance.
- clinicaltrials: ClinicalTrials.gov registry, all registrations per substance.
- openfda: FDA CAERS reports of harm after food and supplement products.
- cyberleninka: Russian-language journals.
- reddit: posts in r/Supplements, r/Nootropics, r/Biohackers via the Arctic Shift archive.

## Evidence levels

{levels}

The level comes from the source's own publication type and MeSH terms; where the source gives none, from words in the
title and abstract (`level_by_keywords = true`). `zone`: cause (meta-analysis, RCT), link (observational designs),
hypothesis (case reports, animal and cell studies, narrative reviews, people's posts).

## Columns

`findings`: id, source, source_id, kind (science, registry, safety, people), level, level_label, zone, substance
(id in `substances`), title, text, text_license, url, published, authors, journal, doi, pmid, lang, cited_by,
retracted, about_intake (the paper is about taking the substance, not the molecule in the body), level_by_keywords,
also_in (other sources that returned the same paper), fetched_at.

`substances`: id, name_ru, names_en (search names), verdict on placebo.wiki.

## Licenses

Full text is included for {with_text} findings, only where redistribution is allowed:

- ClinicalTrials.gov and openFDA: US government works, public domain.
- Europe PMC open-access articles: the abstract under the article's own license (see the article).
- Paywalled Europe PMC abstracts belong to their publishers, CyberLeninka licenses differ per article: text omitted,
  title, authors, journal and link kept.
- Reddit posts belong to their authors: only link, date, community and score kept.

Labels, levels and the compilation: CC BY 4.0, credit placebo.wiki.

## Caveats

- Not medical advice. Levels are assigned by code, not by people; a paper can be mislabelled.
- Search is by substance names in titles and by phrases like "<name> supplementation" in abstracts: papers that name the
  substance differently are missed, and papers about the body's own molecule can slip in (see `about_intake`).
- Collection code: https://github.com/placebo-wiki/placebo-wiki (data/pipeline/harvest).
"""


if __name__ == "__main__":
    main()
