# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""MCP server: evidence-graded answers about dietary supplements, in Russian."""
import json
import pathlib

from mcp.server.fastmcp import FastMCP

CATALOG = json.loads((pathlib.Path(__file__).resolve().parent.parent / "data/catalog.json").read_text())
RANK = {"работает": 0, "зависит": 1, "не подтверждено": 2}

mcp = FastMCP(
    "bady",
    instructions=(
        "Доказательные ответы о БАДах на русском: вердикт (работает / зависит / не подтверждено), "
        "эффекты, дозы, верхние пределы, формы, мифы, взаимодействия и ссылки на исследования. "
        "Начинай с search; по цели (сон, либидо, стресс…) используй by_goal. Цитируй sources."
    ),
)


def _norm(s: str) -> str:
    return s.lower().replace("ё", "е").strip()


def _score(item: dict, q: str) -> int:
    best = 0
    for n in map(_norm, [item["name"], *item["aliases"]]):
        if n == q:
            best = max(best, 100)
        elif n.startswith(q):
            best = max(best, 80)
        elif q in n:
            best = max(best, 60)
        elif len(n) > 2 and n in q:
            best = max(best, 50)
    return best


def _brief(item: dict) -> dict:
    return {"name": item["name"], "verdict": item["verdict"], "grade": item["grade"], "about": item["about"]}


@mcp.tool()
def search(query: str, limit: int = 5) -> list[dict]:
    """Find supplements by name or synonym (Russian or English). Returns name, verdict, evidence grade A-D."""
    q = _norm(query)
    hits = sorted(((s, it) for it in CATALOG["items"] if (s := _score(it, q))), key=lambda x: -x[0])
    return [_brief(it) for _, it in hits[:limit]]


@mcp.tool()
def get_supplement(name: str) -> dict:
    """Full evidence card for one supplement: effects with levels, dose, upper limit, forms, myths, cautions, drug interactions, sources (PMID/DOI)."""
    q = _norm(name)
    hits = sorted(((s, it) for it in CATALOG["items"] if (s := _score(it, q))), key=lambda x: -x[0])
    if not hits:
        return {"error": f"Не найдено: {name}. Вызови search."}
    return hits[0][1]


@mcp.tool()
def by_goal(goal: str) -> list[dict]:
    """Supplements for a goal, most reliable first. Goals: сон, стресс, либидо, потенция, энергия, мышцы, иммунитет, сердце, память, кости и суставы, кожа и волосы, кишечник, вес и сахар, щитовидка, беременность, тестостерон, печень, зрение, климакс."""
    g = _norm(goal)
    rows = []
    for it in CATALOG["items"]:
        if g not in it["goals"]:
            continue
        own = sorted((e for e in it["effects"] if g in e["goals"]), key=lambda e: RANK[e["level"]])
        best = own[0] if own else {"text": it["about"], "level": it["verdict"]}
        rows.append({**_brief(it), "for_goal": best["text"], "level_for_goal": best["level"]})
    rows.sort(key=lambda r: (RANK[r["level_for_goal"]], r["grade"] or "Z"))
    return rows


@mcp.tool()
def list_goals() -> list[str]:
    """All goals by_goal understands."""
    return CATALOG["goals"]


if __name__ == "__main__":
    mcp.run()
