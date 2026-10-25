"""English names for search: names.json maps a catalog id to its names (first is the main one), filled once from the catalog
and Wikidata, then corrected and extended with synonyms by hand."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from collect import english  # noqa: E402

CATALOG = pathlib.Path(__file__).resolve().parents[2] / "catalog.json"
NAMES = pathlib.Path(__file__).with_name("names.json")
LATIN = re.compile(r"[A-Za-z0-9 \-'().,]+")


def load() -> dict:
    raw = json.loads(NAMES.read_text()) if NAMES.exists() else {}
    return {k: v if isinstance(v, list) else [v] for k, v in raw.items() if v}


def fill() -> None:
    names = load()
    for x in json.loads(CATALOG.read_text())["items"]:
        if names.get(x["id"]):
            continue
        en = next((a for a in [x["name"], *x.get("aliases", [])] if LATIN.fullmatch(a)), "")
        try:
            names[x["id"]] = [en or english(x["name"])]
        except Exception as e:
            print(x["name"], e)
            continue
        print(f'{x["name"]} -> {names[x["id"]]}')
    NAMES.write_text(json.dumps(names, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    fill()
