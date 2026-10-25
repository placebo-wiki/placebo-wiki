"""Builds the search catalog (all Brain 25 substances + own entries) for the site and the MCP server."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from nodash import clean  # noqa: E402
from translit import slug  # noqa: E402

B25 = json.loads((ROOT / "src/brain-25-evidence-main/docs/data.json").read_text())
_MAP_FILE = ROOT.parent / "site/data.js"
# The owner's personal supplement list (forms and own entries) is not in the public repository.
MAP = json.loads(clean(_MAP_FILE.read_text()).split("=", 1)[1].rstrip().rstrip(";")) if _MAP_FILE.exists() else {"items": []}

VERDICT = {"работает": "работает", "зависит от контекста": "зависит", "не подтверждено": "не подтверждено"}
STRENGTH = {"сильно": "работает", "умеренно": "работает", "контекст": "зависит", "слабо": "не подтверждено", "маркетинг": "не подтверждено"}

GOALS = {
    "сон": ["сон", "засып", "бессон", "циркад"],
    "стресс": ["стресс", "тревог", "кортизол", "настроен", "депресс", "психик"],
    "либидо": ["либидо", "сексуальн", "тестостерон", "эрекц", "эректил", "влечени"],
    "энергия": ["энерг", "усталост", "выносл", "производительн"],
    "мышцы": ["мышц", "спорт", "сила", "саркопен"],
    "иммунитет": ["иммун", "простуд", "орви", "вирус"],
    "сердце": ["сердц", "сосуд", "давлен", "холестер", "триглицерид"],
    "память": ["когниц", "памят", "внимани", "мозг", "деменц"],
    "кости и суставы": ["кост", "сустав", "перелом", "остеоартрит"],
    "кожа и волосы": ["кож", "волос", "ногт"],
    "кишечник": ["жкт", "кишеч", "диаре", "пищевар", "микробиот"],
    "вес и сахар": ["вес", "жир", "метабол", "диабет", "глюкоз", "ожирен"],
    "щитовидка": ["щитовид", "йод"],
    "беременность": ["беремен", "плод"],
}

ALIASES = {
    "Магний": ["magnesium", "магне б6", "магнезиум", "бисглицинат", "цитрат магния"],
    "Витамин D": ["d3", "д3", "витамин д", "витамин д3", "холекальциферол", "vitamin d"],
    "Витамин K2": ["k2", "к2", "мк-7", "менахинон"],
    "Омега-3": ["омега", "omega", "рыбий жир", "fish oil", "epa", "dha"],
    "Цинк": ["zinc", "пиколинат цинка"],
    "B12": ["б12", "в12", "кобаламин", "метилкобаламин", "цианокобаламин"],
    "B9": ["фолиевая кислота", "фолат", "метилфолат", "б9", "в9"],
    "B6": ["б6", "в6", "пиридоксин"],
    "Мелатонин": ["melatonin"],
    "Креатин": ["creatine", "моногидрат"],
    "Ашваганда": ["ашвагандха", "ashwagandha", "withania"],
    "Ежовик": ["ежовик гребенчатый", "lion's mane", "герициум"],
    "Йохимбин": ["йохимбе", "yohimbine"],
    "Сывороточный протеин": ["протеин", "whey", "сывороточный белок"],
    "L-цитруллин": ["цитруллин", "цитруллин малат", "citrulline"],
    "Аргинин": ["l-аргинин", "arginine"],
    "Пробиотики": ["пробиотик", "probiotic", "бифидобактерии", "лактобактерии"],
    "Йод": ["iodine", "калия йодид", "келп"],
    "Бор": ["boron"],
    "Железо": ["iron", "ферритин"],
    "Кофеин": ["caffeine"],
    "Куркумин": ["куркума", "turmeric", "curcumin"],
    "CoQ10": ["коэнзим", "убихинон", "q10", "ку10"],
    "NAC": ["ацетилцистеин", "n-ацетилцистеин"],
    "Коллаген": ["collagen"],
    "Глицин": ["glycine"],
}

OWN = [
    dict(id="tongkat", name="Тонгкат али", aliases=["эврикома", "eurycoma", "tongkat ali", "тонгкат"]),
    dict(id="forskolin", name="Форсколин", aliases=["колеус", "coleus", "forskolin"]),
    dict(id="soy", name="Протеин соевый", aliases=["соевый белок", "изолят соевого белка", "soy protein"]),
    dict(id="gels", name="Энергетические гели", aliases=["гель", "углеводы на тренировке", "energy gel"]),
]


def goals_of(text: str) -> list[str]:
    t = text.lower()
    return [g for g, words in GOALS.items() if any(re.search(r"(?<![а-яё])" + w, t) for w in words)]


def with_goals(effects: list[dict]) -> list[dict]:
    for e in effects:
        e["goals"] = goals_of(e["text"])
    return effects


def forms_from_map(substance: str) -> list[dict]:
    return [{"name": it["name"], "form": it["form"], "note": it["form_note"]}
            for it in MAP["items"] if it["substance"] == substance]


EVIDENCE_DIR = ROOT / "evidence"
IDISK_DIR = ROOT / "evidence_idisk"


def enrich(rec: dict) -> dict:
    """Adds Europe PMC reviews (metadata only, abstracts stay local) and iDISK interactions."""
    ev = EVIDENCE_DIR / f"{rec['id']}.json"
    if ev.exists():
        d = json.loads(ev.read_text())
        rec["reviews_total"] = d["hits"]
        rec["reviews"] = [{k: x.get(k) for k in ("pmid", "doi", "title", "year", "cited_by")} for x in d["items"][:10]]
    idk = IDISK_DIR / f"{rec['id']}.json"
    if idk.exists():
        d = json.loads(idk.read_text())
        rec["idisk_interactions"] = [{"drug": x["drug"], "note": x["note"]} for x in d["interactions"]]
        rec["idisk_adverse"] = d["adverse_reactions"]
    return rec


def build():
    out = []
    for b in B25:
        effects = with_goals([{"text": m[1], "level": STRENGTH.get(m[2], "зависит")} for m in (b.get("mechs") or [])])
        blob = " ".join([b.get("category", ""), " ".join(b.get("effects") or []), " ".join(e["text"] for e in effects)])
        out.append({
            "id": slug(b["id"]), "name": b["name"], "aliases": ALIASES.get(b["id"], []),
            "verdict": VERDICT[b["verdict"]], "grade": b.get("grade"), "category": b.get("category"),
            "goals": goals_of(blob), "about": b.get("about"), "who_needs": b.get("who_needs"), "effects": effects,
            "dosage": b.get("dosage"), "upper_limit": b.get("upper_limit"), "onset": b.get("onset"), "course": b.get("course"),
            "forms_note": b.get("forms") or b.get("how_to_choose"), "forms": forms_from_map(b["id"]),
            "food": b.get("food_sources"), "myths": b.get("myths"), "caution": b.get("caution"),
            "interactions": b.get("interactions") or [],
            "sources": [{"pmid": s.get("pmid"), "title": s.get("title"), "year": s.get("year"), "doi": s.get("doi"),
                         "type": ", ".join(s.get("pubtype") or [])} for s in (b.get("key_sources") or [])[:6]],
            "origin": "Brain 25 Evidence (MIT)",
        })
    for o in OWN:
        it = next((x for x in MAP["items"] if x["id"] == o["id"]), None)
        if it is None:
            continue
        effects = with_goals([{"text": e["text"], "level": e["level"]} for e in it["effects"]])
        out.append({
            "id": o["id"], "name": o["name"], "aliases": o["aliases"], "verdict": it["verdict"], "grade": it["grade"],
            "category": it["group"], "goals": goals_of(" ".join(e["text"] for e in effects) + " " + it["about"]),
            "about": it["about"], "who_needs": it["who_needs"], "effects": effects, "dosage": it.get("dosage"),
            "upper_limit": None, "onset": None, "course": None, "forms_note": it["form_note"],
            "forms": [{"name": it["name"], "form": it["form"], "note": it["form_note"]}], "food": None, "myths": None,
            "caution": None, "interactions": [], "sources": it["sources"], "origin": "PubMed",
        })
    out = [enrich(r) for r in out]
    text = clean(json.dumps({"goals": list(GOALS), "items": out}, ensure_ascii=False, indent=1))
    (ROOT / "catalog.json").write_text(text)
    (ROOT.parent / "site/catalog.js").write_text("window.CATALOG = " + text + ";\n")
    print(len(out), "substances")


if __name__ == "__main__":
    build()
