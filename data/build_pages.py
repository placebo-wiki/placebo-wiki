"""Renders one static HTML page per supplement and per goal, plus sitemap.xml, so search engines and AI assistants can cite them."""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT.parent / "site"
sys.path.insert(0, str(ROOT.parent / "tools"))
from nodash import clean  # noqa: E402
from translit import slug as goal_slug  # noqa: E402

CAT = json.loads((ROOT / "catalog.json").read_text())
BASE = "https://placebo.wiki"
LV = {"работает": "w", "зависит": "d", "не подтверждено": "n"}
LV_TEXT = {"работает": "работает", "зависит": "зависит от условий", "не подтверждено": "не доказано"}
RANK = {"работает": 0, "зависит": 1, "не подтверждено": 2}
GRADE = {"A": "много крупных обзоров", "B": "есть хорошие испытания", "C": "мало испытаний", "D": "почти нет данных на людях"}
e = html.escape


def page(title: str, desc: str, body: str, path: str, ld: dict) -> str:
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/{path}"><link rel="icon" href="../favicon.ico" sizes="32x32"><link rel="icon" href="../img/logo.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="../img/icon-180.png"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="https://placebo.wiki/img/og.png"><meta name="twitter:card" content="summary_large_image"><link rel="preload" href="../fonts/Inter.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="../search.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body class="has-answer">
<nav class="bar"><a href="../" class="bar-mark" id="home" aria-label="placebo.wiki"><svg class="bar-svg" viewBox="0 0 512 512" aria-hidden="true"><defs><mask id="lm"><rect width="512" height="512" fill="#fff"/><g fill="#000" transform="translate(-33 -4)"><rect x="150" y="140" width="64" height="240" rx="32"/><circle cx="266" cy="236" r="96"/><circle class="lm-dot" cx="394" cy="298" r="34"/></g><circle cx="233" cy="232" r="40" fill="#fff"/></mask></defs><rect width="512" height="512" rx="116" fill="currentColor" mask="url(#lm)"/></svg></a><div class="bar-links"><a href="../b/">Все БАДы</a><a href="../about.html">Наши правила</a><a href="../mcp.html">Для агентов</a></div></nav>
<header class="top"><a href="../" class="logo"><span class="logo-word">placebo<span>.wiki</span></span></a>
<form class="field" action="../" role="search"><input name="q" type="search" placeholder="Другой БАД или цель" aria-label="Поиск"><button aria-label="Найти"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button><a class="mymap" href="../profile.html" aria-label="Моя карта здоровья"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg><span class="tip">Моя карта здоровья</span></a></form></header>
<main>{body}</main>
<script src="../metrika.js"></script><script src="../account.js"></script><script>{{const p=document.getElementById("people");if(p)ACC.mountPeople(p,p.dataset.sid);}}</script>
<script>document.documentElement.classList.add("js");const io=new IntersectionObserver((es)=>es.forEach((x)=>{{if(x.isIntersecting){{x.target.classList.add("in");io.unobserve(x.target);}}}}),{{threshold:.1}});document.querySelectorAll(".rv").forEach((el)=>io.observe(el));</script>
<footer><a href="../about.html">Наши правила</a><a href="../privacy.html">Конфиденциальность</a><a href="../mcp.html">MCP для агентов</a><a href="https://github.com/placebo-wiki/placebo-wiki">Открытый код</a><span>Не лекарство. Перед приёмом посоветуйтесь с врачом.</span></footer>
</body></html>"""


def src_link(s: dict) -> str:
    return f"https://doi.org/{s['doi']}" if s.get("doi") else f"https://pubmed.ncbi.nlm.nih.gov/{s['pmid']}/"


def reviews_block(it: dict) -> str:
    ev = ROOT / "evidence" / f"{it['id']}.json"
    if not ev.exists():
        return ""
    d = json.loads(ev.read_text())
    if not d["items"]:
        return ""
    rows = "".join(f'<p class="src"><a href="{src_link(x) if x.get("doi") or x.get("pmid") else "#"}" rel="noopener">{e(x.get("title") or "")}</a> <span class="t">{e(str(x.get("year") or ""))} · цитирований: {x.get("cited_by") or 0}</span></p>' for x in d["items"])
    return f'<details><summary>Обзоры исследований: {d["hits"]} в Europe PMC, самые цитируемые</summary>{rows}</details>'


HEAD = {"работает": "Работает.", "зависит": "Зависит от условий.", "не подтверждено": "Не доказано."}
STUDY = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z«])")


def low1(t: str) -> str:
    return t[0].lower() + t[1:] if re.match(r"[А-ЯЁA-Z][а-яёa-z]", t) else t


def say_line(it: dict, effects: list) -> str:
    def of(lv):
        seen = list(dict.fromkeys(low1(re.split(r"[;(]", x["text"])[0].strip()) for x in effects if x["level"] == lv))
        return [t for i, t in enumerate(seen) if t and 8 <= len(t) <= (42 if i else 60)][:2]
    works, dep = of("работает"), of("зависит")

    def tail():
        a = f" {'Доказано' if it['verdict'] == 'работает' else 'Есть данные'}: {', '.join(works)}." if works else ""
        return a + (f" При условиях: {', '.join(dep)}." if dep else "")
    for cut in ("dep", "works", "dep0"):
        if len(tail()) <= 110:
            break
        if cut == "dep":
            dep = dep[:1]
        elif cut == "works":
            works = works[:1]
        else:
            dep = []
    return f"<b>{HEAD[it['verdict']]}</b>{e(tail())}"


def item_page(it: dict) -> str:
    effects = sorted(it["effects"], key=lambda x: RANK[x["level"]])
    short = f"{it['name']}: {LV_TEXT[it['verdict']]}. {it['about'] or ''}"
    num = lambda k, v: f"<div><span>{k}</span><b>{e(v)}</b></div>" if v else ""  # noqa: E731
    sec = lambda t, b: f'<section class="sec rv"><h2>{t}</h2>{b}</section>'  # noqa: E731
    para = lambda t: '<div class="lines">' + "".join(f"<p>{e(x)}</p>" for x in STUDY.split(t or "") if x) + "</div>"  # noqa: E731
    g = {"A": 4, "B": 3, "C": 2, "D": 1}.get(it["grade"] or "", 0)
    meter = '<span class="meter">' + "".join(f'<i class="{"on" if n <= g else ""}"></i>' for n in range(1, 5)) + "</span>"
    forms = "".join(f"<p>{e(x[:1].upper() + x[1:])}.</p>" for x in re.split(r";\s*", it.get("forms_note") or "") if x)
    forms += "".join(f'<p><b>{e(f["name"])}{", " + e(f["form"]) if f["form"] else ""}.</b> {e(f["note"])}</p>' for f in it["forms"])
    body = f"""<article class="card story">
{f'<p class="kicker">{e(it["category"].split("/")[0])}</p>' if it.get("category") else ""}
<h1>{e(it['name'])}</h1>
<p class="say">{say_line(it, effects)}</p>
<div class="grade">{meter}{GRADE.get(it['grade'] or '', '')}</div>
<div class="nums rv">{num('Доза', it['dosage'])}{num('Предел', it['upper_limit'])}{num('Эффект через', it['onset'])}{num('Кому нужно', it['who_needs'])}</div>
{sec('Суть', f'<p class="big">{e(it["about"] or "")}</p>')}
{sec('Что говорят исследования', ''.join(f'<div class="ef"><span>{e(x["text"])}</span><span class="badge b-{LV[x["level"]]}">{LV_TEXT[x["level"]]}</span></div>' for x in effects))}
{sec('Форма важна', f'<div class="lines">{forms}</div>') if forms else ''}
{sec('Мифы', para(it.get('myths'))) if it.get('myths') else ''}
{sec('Осторожно', para(it.get('caution'))) if it.get('caution') else ''}
{sec('С лекарствами', ''.join(f'<div class="ef"><span>{e(x["with"][:1].upper() + x["with"][1:])}</span><span class="mlabel">{e(x["note"])}</span></div>' for x in it['interactions'])) if it['interactions'] else ''}
{sec('Из еды', f'<p class="big">{e(it["food"])}</p>') if it.get('food') else ''}
<section class="sec people" id="people" data-sid="{e(it['id'])}" hidden></section>
{sec('Источники', ''.join(f'<p class="src"><a href="{src_link(s)}" rel="noopener">{e(s["title"] or "")}</a> <span class="t">{s.get("year") or ""} {e(s.get("type") or "")}</span></p>' for s in it['sources']) + reviews_block(it) + f'<p class="text mlabel">Оценка: {e(it["origin"])}.</p>')}
</article>"""
    ld = {"@context": "https://schema.org", "@type": "MedicalWebPage", "name": f"{it['name']}: работает ли, доза, исследования",
          "about": {"@type": "DietarySupplement", "name": it["name"]}, "inLanguage": "ru",
          "citation": [src_link(s) for s in it["sources"]]}
    body = re.sub(r"\s?\((\d{7,8})\)", r' <a class="pmid" href="https://pubmed.ncbi.nlm.nih.gov/\1/" rel="noopener">PubMed</a>', body)
    return page(f"{it['name']}: работает ли, доза, исследования", short[:160], body, f"b/{it['id']}.html", ld)


def goal_page(goal: str, slug: str) -> str:
    rows = []
    for it in CAT["items"]:
        if goal not in it["goals"]:
            continue
        own = sorted((x for x in it["effects"] if goal in x["goals"]), key=lambda x: RANK[x["level"]])
        rows.append((it, own[0] if own else {"text": it["about"], "level": it["verdict"]}))
    rows.sort(key=lambda r: (RANK[r[1]["level"]], r[0]["grade"] or "Z"))
    works = sum(1 for _, b in rows if b["level"] == "работает")
    lead = f"Доказано работают: {works} из {len(rows)}." if works else "Надёжно доказанного нет."
    body = f"""<article class="card"><h1>БАДы: {e(goal)}</h1><p class="lead">{lead} Сначала самое надёжное.</p><div class="list">
{''.join(f'<a class="row" href="../b/{it["id"]}.html"><div><div class="nm">{e(it["name"])}</div><div class="ef">{e(b["text"] or "")}</div></div><span class="badge b-{LV[b["level"]]}">{LV_TEXT[b["level"]]}</span></a>' for it, b in rows)}
</div></article>"""
    ld = {"@context": "https://schema.org", "@type": "MedicalWebPage", "name": f"БАДы для цели «{goal}» по исследованиям", "inLanguage": "ru"}
    return page(f"БАДы для цели «{goal}»: что работает по исследованиям", f"{lead} Список БАДов для цели «{goal}» по обзорам исследований.", body, f"g/{slug}.html", ld)


def index_page() -> str:
    items = sorted(CAT["items"], key=lambda it: it["name"].lower())
    groups = {}
    for it in items:
        groups.setdefault(it["name"][0].upper(), []).append(it)
    goals = "".join(f'<a class="chip" href="../g/{goal_slug(g)}.html">{e(g)}</a>' for g in CAT["goals"])
    works = sum(1 for it in items if it["verdict"] == "работает")
    seg = "".join(f'<label><input type="radio" name="v" value="{v}"{" checked" if v == "all" else ""}><span>{t}</span></label>'
                  for v, t in (("all", "Все"), ("w", "Работает"), ("d", "Зависит"), ("n", "Не доказано")))
    rows = "".join(f'<section class="az"><h2>{e(k)}</h2>' + "".join(
        f'<a class="row" data-v="{LV[it["verdict"]]}" href="{it["id"]}.html"><div><div class="nm">{e(it["name"])}</div><div class="ef">{e(it["about"] or "")}</div></div><span class="badge b-{LV[it["verdict"]]}">{LV_TEXT[it["verdict"]]}</span></a>'
        for it in g) + "</section>" for k, g in groups.items())
    body = f"""<article class="card story"><p class="kicker">Каталог</p><h1>Все БАДы</h1>
<p class="say"><b>{len(items)} добавки.</b> Доказано работают {works}. Остальные помогают только при условиях или не доказаны.</p>
<h2>По целям</h2><div class="goal-chips">{goals}</div>
<div class="seg filter">{seg}</div>
<div class="list" id="az">{rows}</div></article>
<script>{{const az=document.getElementById("az");document.querySelectorAll(".filter input").forEach((r)=>r.onchange=()=>{{az.querySelectorAll(".row").forEach((x)=>x.hidden=r.value!=="all"&&x.dataset.v!==r.value);az.querySelectorAll(".az").forEach((s)=>s.hidden=![...s.querySelectorAll(".row")].some((x)=>!x.hidden));}});}}</script>"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Все БАДы: что работает по исследованиям", "inLanguage": "ru"}
    return page("Все БАДы по алфавиту: что работает по исследованиям", f"{len(items)} добавок с оценкой по обзорам исследований: доказано работают {works}.", body, "b/index.html", ld)


def build():
    (SITE / "b").mkdir(exist_ok=True)
    (SITE / "g").mkdir(exist_ok=True)
    urls = [f"{BASE}/", f"{BASE}/about.html", f"{BASE}/profile.html", f"{BASE}/privacy.html"]
    (SITE / "b" / "index.html").write_text(clean(index_page()))
    urls.append(f"{BASE}/b/")
    for it in CAT["items"]:
        (SITE / "b" / f"{it['id']}.html").write_text(clean(item_page(it)))
        urls.append(f"{BASE}/b/{it['id']}.html")
    for g in CAT["goals"]:
        s = goal_slug(g)
        (SITE / "g" / f"{s}.html").write_text(clean(goal_page(g, s)))
        urls.append(f"{BASE}/g/{s}.html")
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(len(urls), "urls")


if __name__ == "__main__":
    build()
