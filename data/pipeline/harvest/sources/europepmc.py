"""Europe PMC: PubMed plus European sources; publication types and MeSH give the evidence level."""
import re
import urllib.parse

from net import get

# same filter as ../collect.py: a paper about taking the substance, not about the body's own molecule
INTAKE = re.compile(r"\b(supplement\w*|intake|administration|dietary|oral|capsule|extract|consumption|treatment|therapy|randomi[sz]ed)\b", re.I)

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


ANIMALS = {"mice", "rats", "disease models, animal", "mice, transgenic", "mice, knockout", "rats, sprague-dawley",
           "rats, wistar", "swine", "dogs", "rabbits", "zebrafish", "drosophila melanogaster", "caenorhabditis elegans"}


def level(pub_types: list[str], mesh: list[str]) -> str:
    pt, mh = {p.lower() for p in pub_types}, {m.lower() for m in mesh}
    if pt & {"meta-analysis", "systematic review", "systematic-review"}:
        return "meta"
    if "randomized controlled trial" in pt:
        return "rct"
    if any(p.startswith("clinical trial") for p in pt) or "controlled clinical trial" in pt:
        return "trial"
    if pt & {"case reports", "case-report"}:
        return "case"
    # MeSH tags human disease studies that use mice with "Humans" too, so species terms decide
    if mh & ANIMALS or ("animals" in mh and "humans" not in mh) or "in vitro techniques" in mh:
        return "animal_cell"
    if "case-control studies" in mh:
        return "case_control"
    if mh & {"cohort studies", "prospective studies", "longitudinal studies"}:
        return "cohort"
    if "cross-sectional studies" in mh:
        return "cross_sectional"
    if "observational study" in pt:
        return "observational"
    if "review" in pt or "review-article" in pt:
        return "review"
    return "unknown"


PASSES = [  # meta-analyses and RCTs are taken in full; the rest is capped by --limit, most cited first
    '(PUB_TYPE:"meta-analysis" OR PUB_TYPE:"systematic-review")',
    'PUB_TYPE:"randomized controlled trial"',
    None,
]
FULL_CAP = 20000


def query(names: list[str]) -> str:
    # a bare name in the abstract drags in lab markers ("creatine kinase"), so the abstract must say it was taken
    parts = [f'TITLE:"{n}" OR ABSTRACT:"{n} supplementation" OR ABSTRACT:"{n} supplement" OR ABSTRACT:"{n} intake"'
             for n in names]
    return "(" + " OR ".join(parts) + ") AND SRC:MED"


def fetch(substance: dict, limit: int):
    base_q = query(substance.get("names") or [substance["en"]])
    for flt in PASSES:
        q = f"{base_q} AND {flt}" if flt else base_q
        yield from search(q, FULL_CAP if flt else limit)


def search(q: str, limit: int):
    cursor, got = "*", 0
    while got < limit:
        page = min(1000, limit - got)
        url = f"{API}?query={urllib.parse.quote(q)}&format=json&resultType=core&pageSize={page}" \
              f"&cursorMark={urllib.parse.quote(cursor)}&sort={urllib.parse.quote('CITED desc')}"
        data = get(url)
        rows = data.get("resultList", {}).get("result", [])
        for x in rows:
            types = (x.get("pubTypeList") or {}).get("pubType", [])
            mesh = [m.get("descriptorName", "") for m in (x.get("meshHeadingList") or {}).get("meshHeading", [])]
            yield {
                "source": "europepmc", "source_id": x["id"], "kind": "science", "level": level(types, mesh),
                "title": x.get("title"), "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x.get("abstractText") or "")).strip(),
                "url": f"https://europepmc.org/article/MED/{x['id']}", "published": x.get("firstPublicationDate"),
                "authors": x.get("authorString"), "journal": ((x.get("journalInfo") or {}).get("journal") or {}).get("title"),
                "doi": (x.get("doi") or "").lower() or None, "pmid": x.get("pmid"), "lang": x.get("language"),
                "extra": {"pub_types": types, "mesh": mesh, "cited_by": x.get("citedByCount"),
                          "retracted": any("retract" in t.lower() for t in types),
                          "intake": bool(INTAKE.search(f"{x.get('title')} {x.get('abstractText')}")), "open_access": x.get("isOpenAccess") == "Y"},
            }
        got += len(rows)
        nxt = data.get("nextCursorMark")
        if not rows or not nxt or nxt == cursor:
            return
        cursor = nxt
