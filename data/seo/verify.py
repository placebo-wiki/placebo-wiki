"""Checks an article against docs/formula.md: numbers from the card, wording no stronger than the evidence, banned words, required parts."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT = {it["id"]: it for it in json.loads((ROOT / "catalog.json").read_text())["items"]}

BANNED = ["лечит", "излечива", "вылечива", "гарантир", "чудо", "детокс", "шлак", "очищает организм", "без побочн",
          "абсолютно безопас", "всем нужен", "обязательно пить", "100%", "мгновенно", "навсегда", "лучший"]
STRONG = ["доказано", "доказан", "доказыва", "точно помогает", "несомненно", "однозначно"]
REQUIRED = ["Источники", "Обновлено", "Не является лекарственным средством"]
NUM = re.compile(r"\d+(?:[.,]\d+)?")
DASH = chr(0x2014)
KEEP = ("name", "aliases", "verdict", "grade", "about", "who_needs", "dosage", "upper_limit", "onset",
        "course", "forms_note", "myths", "caution", "food")


def card_numbers(card: dict) -> set[str]:
    """Only numbers the writer can see: visible fields, effects, interactions, source titles and years.
    Review metadata (citation counts, pmids of top reviews) is not a legal alibi."""
    parts = [json.dumps(card.get(k) or "", ensure_ascii=False) for k in KEEP]
    parts += [json.dumps(x, ensure_ascii=False) for x in card.get("effects") or []]
    parts += [json.dumps(x, ensure_ascii=False) for x in card.get("interactions") or []]
    parts += [f"{s.get('title') or ''} {s.get('year') or ''}" for s in card.get("sources") or []]
    text = re.sub(r"(\d)[  ](?=\d{3}\b)", r"\1", " ".join(parts))
    return {n.replace(",", ".") for n in NUM.findall(text)}


def check(article: str, card_id: str) -> list[str]:
    card = CAT[card_id]
    low = article.lower()
    errors = []
    allowed = card_numbers(card)
    body = re.sub(r"Обновлено[^\n]*", "", article.split("Источники")[0])
    body = re.sub(r"(\d)[  ](?=\d{3}\b)", r"\1", body)
    for n in NUM.findall(body):
        if n.replace(",", ".") not in allowed:
            errors.append(f"число {n} не из карточки")
    errors += [f"запретное слово «{w}»" for w in BANNED if w in low]
    if not (card["verdict"] == "работает" and card.get("grade") == "A"):
        claims = re.sub(r"не\s*доказ\w*|«[^»]*»", "", low)
        errors += [f"слово «{w}» сильнее уровня данных ({card['verdict']}, {card.get('grade')})" for w in STRONG if w in claims]
    errors += [f"нет обязательной части «{r}»" for r in REQUIRED if r.lower() not in low]
    if DASH in article:
        errors.append("длинное тире")
    refs = [s.get("doi") or s.get("pmid") for s in card["sources"] if s.get("doi") or s.get("pmid")]
    if not any(r in article for r in refs):
        errors.append("нет ни одной ссылки на источник из карточки")
    return errors


if __name__ == "__main__":
    errs = check(pathlib.Path(sys.argv[1]).read_text(), sys.argv[2])
    print("\n".join(errs) if errs else "OK")
    sys.exit(1 if errs else 0)
