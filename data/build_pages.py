"""Renders one static HTML page per supplement and per goal, plus sitemap.xml, so search engines and AI assistants can cite them."""
import datetime
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
BY = {it["id"]: it for it in CAT["items"]}

# Article pages (data/seo/articles/<id>.md) go out in batches: at most ART_PER_DAY new
# pages per day (spec docs/chain/2026-10-25-seo/spec.md, R-6). State: data/seo/released.json.
SEO = ROOT / "seo"
ART = SEO / "articles"
REL = SEO / "released.json"
ART_PER_DAY = 50
# Wordstat demand (site/top.json, 30 days): the most-searched supplements are released first.
WORDSTAT_TOP = ["Магний", "Коллаген", "Витамин D", "Омега-3", "Глицин"]

HAS_ART = False  # set by build() when a released batch of articles exists

# Translations: data/seo/i18n/<lang>/<id>.md, interface strings in langs.json.
# Language order is his list of 25.10 (Russian is the source, not in the list).
I18N = SEO / "i18n"
LANGS = json.loads((I18N / "langs.json").read_text())
LANG_ORDER = LANGS["order"]
LV = {"работает": "w", "зависит": "d", "не подтверждено": "n"}
LV_TEXT = {"работает": "работает", "зависит": "зависит от условий", "не подтверждено": "не доказано"}
RANK = {"работает": 0, "зависит": 1, "не подтверждено": 2}
GRADE = {"A": "много крупных обзоров", "B": "есть хорошие испытания", "C": "мало испытаний", "D": "почти нет данных на людях"}
e = html.escape


def page(title: str, desc: str, body: str, path: str, ld: dict, lang: str = "ru", direction: str = "ltr", alt: str = "") -> str:
    rtl = f' dir="{direction}"' if direction != "ltr" else ""
    return f"""<!doctype html>
<html lang="{lang}"{rtl}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/{path}">{alt}<link rel="icon" href="../favicon.ico" sizes="32x32"><link rel="icon" href="../img/logo.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="../img/icon-180.png"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:image" content="https://placebo.wiki/img/og.png"><meta name="twitter:card" content="summary_large_image"><link rel="preload" href="../fonts/Geist-cyrillic.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="../search.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body class="has-answer">
<a class="skip" href="#main">К содержимому</a><nav class="bar"><a href="../" class="bar-mark" id="home" aria-label="placebo.wiki"><svg class="bar-svg" viewBox="0 0 512 512" aria-hidden="true"><defs><mask id="lm"><rect width="512" height="512" fill="#fff"/><g fill="#000" transform="translate(-33 -4)"><rect x="150" y="140" width="64" height="240" rx="32"/><circle cx="266" cy="236" r="96"/><circle class="lm-dot" cx="394" cy="298" r="34"/></g><circle cx="233" cy="232" r="40" fill="#fff"/></mask></defs><rect width="512" height="512" rx="116" fill="currentColor" mask="url(#lm)"/></svg></a><div class="bar-links"><a href="../b/">Все БАДы</a>{'<a href="../s/">Статьи</a>' if HAS_ART else ''}<a href="../about.html">Наши правила</a><a href="../mcp.html">Для агентов</a></div></nav>
<header class="top"><a href="../" class="logo"><span class="logo-word">placebo<span>.wiki</span></span></a>
<form class="field" action="../" role="search"><input name="q" type="search" placeholder="Другой БАД или цель" aria-label="Поиск"><button aria-label="Найти"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button><a class="mymap" href="../profile.html" aria-label="Моя карта здоровья"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg><span class="tip">Моя карта здоровья</span></a></form></header>
<main id="main">{body}</main>
<script src="../metrika.js"></script><script src="../ev.js"></script><script src="../account.js"></script><script>{{const p=document.getElementById("people");if(p)ACC.mountPeople(p,p.dataset.sid);}}</script>
<script>document.documentElement.classList.add("js");const io=new IntersectionObserver((es)=>es.forEach((x)=>{{if(x.isIntersecting){{x.target.classList.add("in");io.unobserve(x.target);}}}}),{{threshold:.1}});document.querySelectorAll(".words").forEach((p)=>{{p.innerHTML=p.innerHTML.split(" ").map((w,i)=>`<span style="--i:${{i}}">${{w}}</span>`).join(" ");}});document.querySelectorAll(".rv").forEach((el)=>io.observe(el));</script>
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


def studies(n: int) -> str:
    word = "исследование" if n % 10 == 1 and n % 100 != 11 else "исследования" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "исследований"
    return f"{n:,}".replace(",", "\u00a0") + " " + word


def from_studies(n: int) -> str:
    word = "исследования" if n % 10 == 1 and n % 100 != 11 else "исследований"
    return f"{n:,}".replace(",", "\u00a0") + " " + word


try:
    from PIL import ImageFont
    SERP_FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
except (ImportError, OSError):
    SERP_FONT = None


def fits(title: str) -> bool:
    """True when the title fits one line of a desktop search result (20px Arial, about 600px) with a margin."""
    return SERP_FONT.getlength(title) <= 580 if SERP_FONT else len(title) <= 56


def study_count(sid: str) -> int:
    f = SITE / "b" / "ev" / f"{sid}.json"
    return sum(json.loads(f.read_text())["n"]) if f.exists() else 0


def patched_note(it: dict) -> str:
    p = it.get("patched")
    if not p or not p.get("pmids"):
        return ""
    links = ", ".join(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{m}/" rel="noopener">{m}</a>' for m in p["pmids"])
    return f'<p class="text mlabel">Уровни уточнены по свежим обзорам: {links}.</p>'


def item_page(it: dict, art: bool = False) -> str:
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
<figure class="evf" data-src="ev/{e(it['id'])}.json"></figure>
<div class="nums rv">{num('Доза', it['dosage'])}{num('Предел', it['upper_limit'])}{num('Эффект через', it['onset'])}{num('Кому нужно', it['who_needs'])}</div>
{f'<div class="list"><a class="row" href="../s/{e(it["id"])}.html"><div><div class="nm">Статья: {e(it["name"])}</div><div class="ef">Подробнее простыми словами: для чего, как принимать, мифы, сочетания</div></div><span class="badge b-w">Читать</span></a></div>' if art else ''}
{sec('Суть', f'<p class="big words">{e(it["about"] or "")}</p>')}
{sec('Что говорят исследования', ''.join(f'<div class="ef"><span>{e(x["text"])}</span><span class="badge b-{LV[x["level"]]}">{LV_TEXT[x["level"]]}</span></div>' for x in effects))}
{sec('Форма важна', f'<div class="lines">{forms}</div>') if forms else ''}
{sec('Мифы', para(it.get('myths'))) if it.get('myths') else ''}
{sec('Осторожно', para(it.get('caution'))) if it.get('caution') else ''}
{sec('С лекарствами', ''.join(f'<div class="ef"><span>{e(x["with"][:1].upper() + x["with"][1:])}</span><span class="mlabel">{e(x["note"])}</span></div>' for x in it['interactions'])) if it['interactions'] else ''}
{sec('Из еды', f'<p class="big">{e(it["food"])}</p>') if it.get('food') else ''}
<section class="sec people" id="people" data-sid="{e(it['id'])}" hidden></section>
{sec('Источники', ''.join(f'<p class="src"><a href="{src_link(s)}" rel="noopener">{e(s["title"] or "")}</a> <span class="t">{s.get("year") or ""} {e(s.get("type") or "")}</span></p>' for s in it['sources']) + reviews_block(it) + patched_note(it) + f'<p class="text mlabel">Оценка: {e(it["origin"])}.</p>')}
</article>"""
    qa = [(f"{it['name']}: работает ли?", re.sub(r"<[^>]+>", "", say_line(it, effects))),
          (f"{it['name']}: какая доза?", it.get("dosage")),
          (f"{it['name']}: через сколько действует?", it.get("onset")),
          (f"{it['name']}: с какими лекарствами нельзя?", "; ".join(f"{x['with']}: {x['note']}" for x in it["interactions"][:4]))]
    ld = {"@context": "https://schema.org", "@graph": [
          {"@type": "MedicalWebPage", "name": f"{it['name']}: работает ли, доза, исследования",
           "about": {"@type": "DietarySupplement", "name": it["name"]}, "inLanguage": "ru",
           "citation": [src_link(s) for s in it["sources"]]},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa if a]}]}
    body = re.sub(r"\s?\((\d{7,8})\)", r' <a class="pmid" href="https://pubmed.ncbi.nlm.nih.gov/\1/" rel="noopener">PubMed</a>', body)
    n = study_count(it["id"])
    if n:
        nm, k = it["name"], f"{round(n / 1000)}\u00a0тыс. исследований" if n >= 1000 else None
        tries = [f"{nm}: выжимка из {from_studies(n)}. Другие сайты не читайте", f"{nm}: выжимка из {from_studies(n)}. Дальше не читайте",
                 f"{nm}: выжимка {from_studies(n)}. Дальше не читайте", f"{nm}: выжимка {k}. Дальше не читайте" if k else "",
                 f"{nm}: выжимка из исследований. Дальше не читайте", f"{nm}: выжимка из {from_studies(n)}"]
        title = next((t for t in tries if t and fits(t)), nm)
        desc = f"Всё на одной странице: работает ли, доза, мифы, с чем нельзя. Собрали {studies(n)} и оставили сильнейшие. Вердикт: {LV_TEXT[it['verdict']]}."
        desc = (desc + " Без рекламы и нейрослопа.") if len(desc) <= 134 else desc
    else:
        title, desc = f"{it['name']}: работает ли, доза, исследования", short[:160]
    return page(title, desc, body, f"b/{it['id']}.html", ld)


def indirect_rows(goal: str) -> str:
    rows = []
    for it in CAT["items"]:
        for x in it.get("indirect") or []:
            if x["goal"] == goal:
                rows.append((it, x))
    if not rows:
        return ""
    rows.sort(key=lambda r: RANK[r[1]["level"]])
    body = "".join(
        f'<a class="row" href="../b/{it["id"]}.html"><div><div class="nm">{e(it["name"])}</div>'
        f'<div class="ef">{e(x["via"])} → {e(goal)}: {e(x["text"])}. {e(x["note"])}</div></div>'
        f'<span class="badge b-{LV[x["level"]]}">{LV_TEXT[x["level"]]}</span></a>' for it, x in rows)
    return f'<h2>Опосредованно</h2><p class="mlabel">Действуют не напрямую, а через посредника; итог не сильнее самого слабого звена цепочки.</p><div class="list">{body}</div>'


def goal_page(goal: str, slug: str) -> str:
    rows = []
    for it in CAT["items"]:
        if goal not in it["goals"]:
            continue
        own = sorted((x for x in it["effects"] if goal in x["goals"]), key=lambda x: RANK[x["level"]])
        # a borrowed verdict never claims "работает" for the goal (his rule of 28.10, now for all goals)
        borrowed = "зависит" if it["verdict"] == "работает" else it["verdict"]
        rows.append((it, own[0] if own else {"text": it["about"], "level": borrowed}))
    rows.sort(key=lambda r: (RANK[r[1]["level"]], r[0]["grade"] or "Z"))
    works = sum(1 for _, b in rows if b["level"] == "работает")
    lead = f"Доказано работают: {works} из {len(rows)}." if works else "Надёжно доказанного нет."
    body = f"""<article class="card"><h1>БАДы: {e(goal)}</h1><p class="lead">{lead} Сначала самое надёжное.</p><div class="list">
{''.join(f'<a class="row" href="../b/{it["id"]}.html"><div><div class="nm">{e(it["name"])}</div><div class="ef">{e(b["text"] or "")}</div></div><span class="badge b-{LV[b["level"]]}">{LV_TEXT[b["level"]]}</span></a>' for it, b in rows)}
</div>{indirect_rows(goal)}</article>"""
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
    return page("Все БАДы по алфавиту: что работает по исследованиям", f"{len(items)} добавок с оценкой по обзорам исследований: доказано работают {works}.", body, "b/", ld)


def released_ids() -> list:
    return [r["id"] for r in json.loads(REL.read_text())["released"]] if REL.exists() else []


def do_release(n: int = ART_PER_DAY) -> None:
    """Marks up to n more articles as released; never more than ART_PER_DAY per calendar day."""
    rel = json.loads(REL.read_text()) if REL.exists() else {"released": []}
    have = {r["id"] for r in rel["released"]}
    today = f"{datetime.date.today():%d.%m.%Y}"
    done_today = sum(1 for r in rel["released"] if r["date"] == today)
    n = max(0, min(n, ART_PER_DAY - done_today))
    top = {name: i for i, name in enumerate(WORDSTAT_TOP)}
    order = sorted(CAT["items"], key=lambda it: (top.get(it["name"], len(top)), -study_count(it["id"])))
    add = [it["id"] for it in order if it["id"] not in have][:n]
    rel["released"] += [{"id": sid, "date": today} for sid in add]
    REL.write_text(json.dumps(rel, ensure_ascii=False, indent=1) + "\n")
    print(f"release: +{len(add)} (сегодня {done_today + len(add)}/{ART_PER_DAY})")


ART_URL = re.compile(r"(https?://[^\s<]+)")


def art_line(t: str) -> str:
    return ART_URL.sub(r'<a href="\1" rel="noopener">\1</a>', e(t.strip()))


def parse_article(sid: str, lang: "str | None" = None):
    """Article .md -> (lead, sections, updated, disclaimer); text escaped, URLs live.
    lang=None reads the Russian original; else data/seo/i18n/<lang>/<id>.md."""
    src = (I18N / lang / f"{sid}.md") if lang else (ART / f"{sid}.md")
    upd_mark = LANGS[lang]["updated"] if lang else "Обновлено:"
    disc_mark = LANGS[lang]["disclaimer"] if lang else "Не является лекарственным"
    lead, secs, upd, disc, buf, cur = "", [], "", "", [], ["", []]
    for ln in src.read_text().split("\n"):
        if ln.startswith("# "):
            continue
        if ln.startswith("## "):
            cur[1].extend(buf)
            buf = []
            cur = [ln[3:].strip(), []]
            secs.append(cur)
        elif ln.startswith("- "):
            buf.append(art_line(ln[2:]))
        elif ln.strip():
            cur[1].extend(buf)
            buf = []
            t = art_line(ln)
            if t.startswith(upd_mark):
                upd = t
            elif t.startswith(disc_mark):
                disc = t
            elif not lead:
                lead = t
            else:
                cur[1].append(t)
    cur[1].extend(buf)
    return lead, secs, upd, disc


def art_paths(sid: str) -> list:
    """Existing translations of the article, in the owner's priority order."""
    return [lg for lg in LANG_ORDER if (I18N / lg / f"{sid}.md").exists()]


def art_name(sid: str, lang: "str | None" = None) -> str:
    """The article's own H1 name (translated when the translation exists)."""
    if lang and (I18N / lang / f"{sid}.md").exists():
        first = (I18N / lang / f"{sid}.md").read_text().split("\n", 1)[0]
        first = first.lstrip("# ").strip()
        return re.split(r"[:：]", first)[0].strip() or BY[sid]["name"]
    return BY[sid]["name"]


def article_page(sid: str, rel: list, lang: "str | None" = None) -> str:
    it = BY[sid]
    L = LANGS.get(lang) if lang else None
    nm = art_name(sid, lang)
    lead, secs, upd, disc = parse_article(sid, lang)
    m = re.match(r"^([^.]{1,60}\.)", lead)
    say = f"<b>{m.group(1)}</b>{lead[m.end():]}" if m else lead
    n = study_count(sid)
    badge = L["verdicts"][it["verdict"]] if L else LV_TEXT[it["verdict"]]
    facts = f'<span class="badge b-{LV[it["verdict"]]}">{badge}</span>'
    if n:
        facts += " " + (L["facts"].format(n=f"{n:,}".replace(",", " ")) if L else f"выжимка из {studies(n)}")
    if not L and GRADE.get(it["grade"] or ""):
        facts += f" · {GRADE[it['grade'] or '']}"
    parts = []
    for title, rows in secs:
        if title == "Источники" and not L:
            body = "".join(f'<p class="src"><a href="{src_link(s)}" rel="noopener">{e(s["title"] or "")}</a> '
                           f'<span class="t">{s.get("year") or ""} {e(s.get("type") or "")}</span></p>'
                           for s in it["sources"] if s.get("pmid") or s.get("doi")) + reviews_block(it)
        else:
            body = '<div class="lines">' + "".join(f"<p>{r}</p>" for r in rows if r) + "</div>"
        parts.append(f'<section class="sec rv"><h2>{e(title)}</h2>{body}</section>')
    links = [src_link(s) for s in it["sources"] if s.get("pmid") or s.get("doi")]
    card_nm = L["card_nm"].format(name=nm) if L else f"Карточка: {nm}"
    card_ef = L["card_ef"] if L else "Доза, предел, формы и оценки по обзорам"
    card_row = (f'<div class="list"><a class="row" href="../b/{e(sid)}.html"><div>'
                f'<div class="nm">{e(card_nm)}</div><div class="ef">{e(card_ef)}</div></div>'
                f'<span class="badge b-{LV[it["verdict"]]}">{e(badge)}</span></a></div>')
    shared = [x for x in rel if x != sid and set(BY[x]["goals"]) & set(it["goals"])
              and (not L or (I18N / lang / f"{x}.md").exists())]
    related = sorted(shared, key=lambda x: -study_count(x))[:4]
    rel_block = ""
    if related:
        rel_block = (f'<section class="sec rv"><h2>{e(L["read_too"] if L else "Читайте также")}</h2><div class="list">'
                     + "".join(f'<a class="row" href="{e(x)}.html"><div><div class="nm">{e(art_name(x, lang))}</div></div>'
                               f'<span class="badge b-{LV[BY[x]["verdict"]]}">{e(L["verdicts"][BY[x]["verdict"]] if L else LV_TEXT[BY[x]["verdict"]])}</span></a>'
                               for x in related)
                     + "</div></section>")
    kicker = L["kicker"] if L else "Статья"
    h1sub = L["h1sub"] if L else ": помогает ли и как принимать"
    body = f"""<article class="card story">
<p class="kicker">{e(kicker)}</p>
<h1>{e(nm)}<span class="h1sub">{e(h1sub)}</span></h1>
<p class="say">{say}</p>
<div class="grade">{facts}</div>
<figure class="evf" data-src="../b/ev/{e(sid)}.json"></figure>
{''.join(parts)}
{f'<p class="mlabel">{upd}</p>' if upd else ''}
{f'<p class="mlabel">{disc}</p>' if disc else ''}
{card_row}
{rel_block}
</article>"""
    plain = re.sub(r"<[^>]+>", "", say)
    howto = next((rows for title, rows in secs if title == "Как принимать"), [])
    # FAQ answers come from the article itself, not from the card fields: no verbatim duplication of the card page
    qa = [(f"{nm}: помогает ли?", plain),
          (f"{nm}: как принимать?", re.sub(r"<[^>]+>", "", " ".join(howto)))]
    h1text = f"{nm}{h1sub}"
    ld = {"@context": "https://schema.org", "@graph": [
          {"@type": "MedicalWebPage", "name": h1text,
           "about": {"@type": "DietarySupplement", "name": nm}, "inLanguage": lang or "ru", "citation": links},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q,
           "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a or "")}} for q, a in qa if a]}]}
    if L:
        tries = [L["title"].format(name=nm), f"{nm}{h1sub}", nm]
    else:
        tries = [f"{nm}: для чего нужен, как принимать, с чем сочетается",
                 f"{nm}: для чего нужен и как принимать",
                 f"{nm}: помогает ли и как принимать",
                 f"{nm}: помогает ли?"]
    title = next((t for t in tries if t and fits(t)), nm)
    if L:
        desc = L["desc"].format(name=nm, verdict=badge)
    else:
        d = (f"Что говорят исследования: работает ли {nm}, в какой дозе, кому осторожно, "
             f"с какими лекарствами нельзя. Вердикт: {LV_TEXT[it['verdict']]}.")
        desc = (d + " Без рекламы и нейрослопа.") if len(d) <= 134 else d
    alts = art_paths(sid)
    alt = ""
    if lang:
        alt = (f'<link rel="alternate" hreflang="ru" href="{BASE}/s/{sid}.html">'
               f'<link rel="alternate" hreflang="x-default" href="{BASE}/s/{sid}.html">'
               + "".join(f'<link rel="alternate" hreflang="{lg}" href="{BASE}/s/{lg}/{sid}.html">'
                         for lg in alts if lg != lang))
    elif alts:
        alt = ("".join(f'<link rel="alternate" hreflang="{lg}" href="{BASE}/s/{lg}/{sid}.html">' for lg in alts)
               + f'<link rel="alternate" hreflang="x-default" href="{BASE}/s/{sid}.html">')
    return page(title, desc, body, f"s/{lang + '/' if lang else ''}{sid}.html", ld,
                lang=lang or "ru", direction=(L["dir"] if L else "ltr"), alt=alt)


def articles_index(rel: list) -> str:
    rows = "".join(
        f'<a class="row" href="{sid}.html"><div><div class="nm">{e(BY[sid]["name"])}</div>'
        f'<div class="ef">{e(BY[sid]["about"] or "")}</div></div>'
        f'<span class="badge b-{LV[BY[sid]["verdict"]]}">{LV_TEXT[BY[sid]["verdict"]]}</span></a>' for sid in rel)
    body = f"""<article class="card story"><p class="kicker">Статьи</p><h1>Статьи о БАДах</h1>
<p class="say"><b>{len(rel)} из {len(CAT['items'])}.</b> Публикуем порциями, не больше 50 в день.</p>
<div class="list">{rows}</div></article>"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Статьи о БАДах по исследованиям", "inLanguage": "ru"}
    return page("Статьи о БАДах: что говорят исследования",
                f"Статьи по {len(rel)} добавкам: работает ли, доза, мифы, сочетания. Только по обзорам исследований.", body, "s/", ld)


def articles_index_lang(lang: str, ids: list) -> str:
    L = LANGS[lang]
    rows = "".join(
        f'<a class="row" href="{sid}.html"><div><div class="nm">{e(art_name(sid, lang))}</div></div>'
        f'<span class="badge b-{LV[BY[sid]["verdict"]]}">{e(L["verdicts"][BY[sid]["verdict"]])}</span></a>' for sid in ids)
    body = f"""<article class="card story"><p class="kicker">{e(L["articles"])}</p><h1>{e(L["articles_index_h1"])}</h1>
<p class="say"><b>{e(L["index_lead"].format(n=len(ids)))}</b></p>
<div class="list">{rows}</div></article>"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": L["articles_index_title"], "inLanguage": lang}
    return page(L["articles_index_title"], L["index_lead"].format(n=len(ids)), body, f"s/{lang}/", ld,
                lang=lang, direction=L["dir"])


def build():
    global HAS_ART
    rel = released_ids()
    HAS_ART = bool(rel)
    stale_file = SEO / "stale.json"
    stale = json.loads(stale_file.read_text()).get("stale", []) if stale_file.exists() else []
    if stale:
        print("ВНИМАНИЕ: статьи устарели после cardfix, нужна перегонка:", ", ".join(x["id"] for x in stale))
    (SITE / "b").mkdir(exist_ok=True)
    (SITE / "g").mkdir(exist_ok=True)
    urls = [f"{BASE}/", f"{BASE}/about.html", f"{BASE}/profile.html", f"{BASE}/privacy.html"]
    lastmod = {}
    sm_alt = {}
    (SITE / "b" / "index.html").write_text(clean(index_page()))
    urls.append(f"{BASE}/b/")
    for it in CAT["items"]:
        (SITE / "b" / f"{it['id']}.html").write_text(clean(item_page(it, it["id"] in rel)))
        urls.append(f"{BASE}/b/{it['id']}.html")
    for g in CAT["goals"]:
        s = goal_slug(g)
        (SITE / "g" / f"{s}.html").write_text(clean(goal_page(g, s)))
        urls.append(f"{BASE}/g/{s}.html")
    if rel:
        (SITE / "s").mkdir(exist_ok=True)
        (SITE / "articles.json").write_text(json.dumps([{"id": s, "name": BY[s]["name"]} for s in rel], ensure_ascii=False))
        (SITE / "s" / "index.html").write_text(clean(articles_index(rel)))
        urls.append(f"{BASE}/s/")
        for sid in rel:
            (SITE / "s" / f"{sid}.html").write_text(clean(article_page(sid, rel)))
            urls.append(f"{BASE}/s/{sid}.html")
            m = re.search(r"Обновлено: (\d{2})\.(\d{2})\.(\d{4})", (ART / f"{sid}.md").read_text())
            if m:
                lastmod[f"{BASE}/s/{sid}.html"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        # Translations of released articles live one level deeper (s/<lang>/), so ../ links shift
        for lg in LANG_ORDER:
            ids = [sid for sid in rel if (I18N / lg / f"{sid}.md").exists()]
            if not ids:
                continue
            (SITE / "s" / lg).mkdir(parents=True, exist_ok=True)
            idx = clean(articles_index_lang(lg, ids))
            idx = idx.replace('href="../', 'href="../../').replace('src="../', 'src="../../').replace('action="../', 'action="../../')
            (SITE / "s" / lg / "index.html").write_text(idx)
            urls.append(f"{BASE}/s/{lg}/")
            for sid in ids:
                h = clean(article_page(sid, rel, lg))
                h = h.replace('href="../', 'href="../../').replace('src="../', 'src="../../').replace('action="../', 'action="../../')
                (SITE / "s" / lg / f"{sid}.html").write_text(h)
                urls.append(f"{BASE}/s/{lg}/{sid}.html")
                ru_url = f"{BASE}/s/{sid}.html"
                if ru_url in lastmod:
                    lastmod[f"{BASE}/s/{lg}/{sid}.html"] = lastmod[ru_url]
                sm_alt[ru_url] = sm_alt.get(ru_url, "") + f'<xhtml:link rel="alternate" hreflang="{lg}" href="{BASE}/s/{lg}/{sid}.html"/>'
                sm_alt[f"{BASE}/s/{lg}/{sid}.html"] = (f'<xhtml:link rel="alternate" hreflang="ru" href="{ru_url}"/>'
                                                       f'<xhtml:link rel="alternate" hreflang="x-default" href="{ru_url}"/>')
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                                      + "".join(f'<url><loc>{u}</loc>{f"<lastmod>{lastmod[u]}</lastmod>" if u in lastmod else ""}{sm_alt.get(u, "")}</url>\n' for u in urls) + "</urlset>\n")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(len(urls), "urls")


if __name__ == "__main__":
    if "--release" in sys.argv:
        i = sys.argv.index("--release")
        n = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else ART_PER_DAY
        do_release(n)
    build()
