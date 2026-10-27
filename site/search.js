document.documentElement.classList.add("js");
const C = window.CATALOG;
let ARTICLES = new Set();
fetch("articles.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : [])).then((a) => { ARTICLES = new Set(a.map((x) => x.id)); }).catch(() => {});
const LV = { "работает": "w", "зависит": "d", "не подтверждено": "n" };
const LV_TEXT = { "работает": "работает", "зависит": "зависит от условий", "не подтверждено": "не доказано" };
const RANK = { "работает": 0, "зависит": 1, "не подтверждено": 2 };
const GRADE = { A: 4, B: 3, C: 2, D: 1 };
const GRADE_TEXT = { 4: "много крупных обзоров", 3: "есть хорошие испытания", 2: "мало испытаний", 1: "почти нет данных на людях" };
const GOAL_WORDS = {
  "тестостерон": ["тестостер"], "потенция": ["потенц", "эрекц", "эректил"], "печень": ["печен", "гепат", "желчн"], "зрение": ["зрени", "глаз", "сетчат"], "климакс": ["климакс", "менопауз", "прилив"],
  "сон": ["сон", "сна", "спать", "засып", "бессон"], "стресс": ["стресс", "тревог", "нерв", "успок", "настроен", "кортизол", "спокойств"],
  "либидо": ["либид", "секс", "влечен"], "энергия": ["энерг", "устал", "бодр", "работоспособ"],
  "мышцы": ["мышц", "масс", "трениров", "спорт", "сил", "выносл"], "иммунитет": ["иммун", "простуд", "болею", "орви"],
  "сердце": ["сердц", "давлен", "сосуд", "холестер"], "память": ["памят", "мозг", "концентр", "внимани", "учеб"],
  "кости и суставы": ["кост", "сустав", "перелом", "связк", "хрящ"], "кожа и волосы": ["кож", "волос", "ногт", "прыщ", "акне", "выпаден"],
  "кишечник": ["кишеч", "живот", "пищевар", "вздут", "диаре", "микрофлор", "жкт", "желуд"], "вес и сахар": ["похуд", "вес", "сахар", "диабет", "жир", "аппетит", "метабол"],
  "щитовидка": ["щитовид"], "беременность": ["беремен", "зачат", "планирован"],
};
const CHIPS = ["сон", "стресс", "либидо", "энергия", "память", "мышцы", "иммунитет", "кожа и волосы"];
const $ = (s) => document.querySelector(s);
const pm = (h) => h.replace(/\s?\((\d{7,8})\)/g, ' <a class="pmid" href="https://pubmed.ncbi.nlm.nih.gov/$1/" target="_blank" rel="noopener">PubMed</a>');
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const norm = (s) => String(s).toLowerCase().replace(/ё/g, "е").replace(/[б]/g, (c) => c).trim();

function score(item, q) {
  const names = [item.name, ...item.aliases].map(norm);
  let best = 0;
  for (const n of names) {
    if (n === q) best = Math.max(best, 100);
    else if (n.startsWith(q)) best = Math.max(best, 80);
    else if (n.includes(q)) best = Math.max(best, 60);
    else if (q.includes(n) && n.length > 2) best = Math.max(best, 50);
  }
  return best;
}

function goalOf(q) {
  if (C.goals.includes(q)) return q;
  return Object.keys(GOAL_WORDS).find((g) => GOAL_WORDS[g].some((w) => q.includes(w)));
}

function find(raw) {
  const q = norm(raw);
  if (!q) return { items: [], goal: null };
  const items = C.items.map((it) => ({ it, s: score(it, q) })).filter((x) => x.s > 0).sort((a, b) => b.s - a.s).map((x) => x.it);
  return { items, goal: goalOf(q) };
}

const EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`";
const RU = "йцукенгшщзхъфывапролджэячсмитьбюё";
const fromLatinLayout = (s) => s.replace(/./g, (c) => (EN.includes(c) ? RU[EN.indexOf(c)] : c));

function dist(a, b) {
  const d = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    let prev = d[0];
    d[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const t = d[j];
      d[j] = Math.min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = t;
    }
  }
  return d[b.length];
}

function nearest(raw) {
  const tries = [norm(raw), norm(fromLatinLayout(norm(raw)))];
  const hit = find(tries[1]).items[0];
  if (hit && tries[1] !== tries[0]) return [hit];
  return C.items
    .map((it) => ({ it, d: Math.min(...[it.name, ...it.aliases].map((n) => dist(tries[0], norm(n)))) }))
    .filter((x) => x.d <= Math.max(2, Math.floor(tries[0].length / 3)))
    .sort((a, b) => a.d - b.d)
    .slice(0, 3)
    .map((x) => x.it);
}

function suggest() {
  const q = $("#q").value;
  if (CHECK.isUrl(q) || CHECK.looksLikeLabel(q)) { $("#sugg").hidden = true; return; }
  const box = $("#sugg");
  const { items, goal } = find(q);
  const rows = [];
  if (goal) rows.push({ label: `Цель: ${goal}`, kind: "что помогает", q: goal });
  for (const it of items.slice(0, 6)) rows.push({ label: it.name, kind: LV_TEXT[it.verdict], q: it.name });
  if (!q.trim() || !rows.length) { box.hidden = true; return; }
  box.innerHTML = rows.map((r, i) => `<button type="button" data-q="${esc(r.q)}" class="${i === 0 ? "sel" : ""}">${esc(r.label)}<span class="kind">${esc(r.kind)}</span></button>`).join("");
  box.hidden = false;
}

const morph = (fn) => (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches ? document.startViewTransition(fn) : fn());

function go(q, push = true) {
  $("#sugg").hidden = true;
  $("#q").value = q;
  if (push) history.pushState({ q }, "", "?q=" + encodeURIComponent(q));
  morph(() => render(q));
  // search runs without page loads, so each answer is sent to the counter as its own page view
  if (window.ym && window.YM_ID) window.ym(window.YM_ID, "hit", location.href, { title: document.title });
}

function meter(g) {
  return `<span class="meter">${[1, 2, 3, 4].map((n) => `<i class="${n <= g ? "on" : ""}"></i>`).join("")}</span>`;
}

function studyTypes(it) {
  let meta = 0, rct = 0;
  for (const s of it.sources) {
    const t = (s.type + " " + s.title).toLowerCase();
    if (t.includes("meta-analysis") || t.includes("systematic review")) meta++;
    else if (t.includes("randomized") || t.includes("trial")) rct++;
  }
  return [meta && `обзоров испытаний: ${meta}`, rct && `испытаний: ${rct}`].filter(Boolean).join(" · ") || `работ: ${it.sources.length}`;
}

const ME = typeof PROFILE !== "undefined" ? PROFILE.load() : null;
function personal(it) {
  if (!ME || PROFILE.isEmpty(ME)) return "";
  const w = PROFILE.warningsFor(it, ME);
  if (!w.length) return `<a class="me ok" href="profile.html">По вашей карте здоровья явных противопоказаний не нашли</a>`;
  return `<div class="me">${w.map((x) => `<p><b>${esc(x.why)}.</b> ${esc(x.text)}</p>`).join("")}<a href="profile.html">Моя карта здоровья</a></div>`;
}

const lines = (t) => String(t || "").split(/(?<=[.!?])\s+(?=[А-ЯЁA-Z«])/).filter(Boolean);
const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
const low1 = (t) => (/^[А-ЯЁA-Z][а-яёa-z]/.test(t) ? t.charAt(0).toLowerCase() + t.slice(1) : t);

function cardHtml(it) {
  const g = GRADE[it.grade] || 0;
  const effects = [...it.effects].sort((a, b) => RANK[a.level] - RANK[b.level]);
  const of = (lv) => [...new Set(effects.filter((e) => e.level === lv).map((e) => low1(e.text.split(/[;(]/)[0].trim())))].filter((t, i) => t && t.length >= 8 && t.length <= (i ? 42 : 60)).slice(0, 2);
  const HEAD = { "работает": "Работает.", "зависит": "Зависит от условий.", "не подтверждено": "Не доказано." };
  let works = of("работает"), dep = of("зависит");
  const tail = () => (works.length ? ` ${it.verdict === "работает" ? "Доказано" : "Есть данные"}: ${works.join(", ")}.` : "") + (dep.length ? ` При условиях: ${dep.join(", ")}.` : "");
  if (tail().length > 110) dep = dep.slice(0, 1);
  if (tail().length > 110) works = works.slice(0, 1);
  if (tail().length > 110) dep = [];
  const say = `<b>${HEAD[it.verdict]}</b>${esc(tail())}`;
  const num = (k, v) => (v ? `<div><span>${k}</span><b>${esc(v)}</b></div>` : "");
  const sec = (title, body) => `<section class="sec rv"><h2>${title}</h2>${body}</section>`;
  const para = (t) => `<div class="lines">${lines(t).map((x) => `<p>${esc(x)}</p>`).join("")}</div>`;
  const forms = it.forms_note ? it.forms_note.split(/;\s*/).map((x) => `<p>${esc(cap(x))}.</p>`).join("") : "";
  return pm(`<article class="card story">
    ${it.category ? `<p class="kicker">${esc(it.category.split("/")[0])}</p>` : ""}
    <h1>${esc(it.name)}</h1>
    ${personal(it)}
    <p class="say">${say}</p>
    <div class="grade">${meter(g)}${GRADE_TEXT[g] || ""}</div>
    <figure class="evf" data-src="b/ev/${esc(it.id)}.json"></figure>
    <div class="nums rv">${num("Доза", it.dosage)}${num("Предел", it.upper_limit)}${num("Эффект через", it.onset)}${num("Кому нужно", it.who_needs)}</div>
    ${ARTICLES.has(it.id) ? `<div class="list"><a class="row" href="s/${esc(it.id)}.html"><div><div class="nm">Статья: ${esc(it.name)}</div><div class="ef">Подробнее простыми словами: для чего, как принимать, мифы, сочетания</div></div><span class="badge b-w">Читать</span></a></div>` : ""}
    ${sec("Суть", `<p class="big">${esc(it.about)}</p>`)}
    ${sec("Что говорят исследования", effects.map((e) => `<div class="ef"><span>${esc(e.text)}</span><span class="badge b-${LV[e.level]}">${LV_TEXT[e.level]}</span></div>`).join(""))}
    ${forms || it.forms.length ? sec("Форма важна", `<div class="lines">${forms}${it.forms.map((f) => `<p><b>${esc(f.name)}${f.form ? ", " + esc(f.form) : ""}.</b> ${esc(f.note)}</p>`).join("")}</div>`) : ""}
    ${it.myths ? sec("Мифы", para(it.myths)) : ""}
    ${it.caution ? sec("Осторожно", para(it.caution)) : ""}
    ${it.interactions.length ? sec("С лекарствами", it.interactions.map((x) => `<div class="ef"><span>${esc(cap(x.with))}</span><span class="mlabel">${esc(x.note)}</span></div>`).join("")) : ""}
    ${it.food ? sec("Из еды", `<p class="big">${esc(it.food)}</p>`) : ""}
    <section class="sec people" id="people" data-sid="${esc(it.id)}" hidden></section>
    ${sec(`Источники · ${studyTypes(it)}`, it.sources.map((s) => `<p class="src"><a href="${s.doi ? "https://doi.org/" + s.doi : "https://pubmed.ncbi.nlm.nih.gov/" + s.pmid}" target="_blank" rel="noopener">${esc(s.title)}</a> <span class="t">${s.year || ""} ${esc(s.type)}</span></p>`).join("") +
      (it.reviews && it.reviews.length ? `<details><summary>Обзоры исследований: ${it.reviews_total} в Europe PMC, самые цитируемые</summary>${it.reviews.map((r) => `<p class="src"><a href="${r.doi ? "https://doi.org/" + r.doi : "https://europepmc.org/article/MED/" + r.pmid}" target="_blank" rel="noopener">${esc(r.title)}</a> <span class="t">${esc(r.year)} · цитирований: ${r.cited_by ?? 0}</span></p>`).join("")}</details>` : "") +
      (it.idisk_interactions && it.idisk_interactions.length ? `<details><summary>Взаимодействия с лекарствами по iDISK: ${it.idisk_interactions.length}</summary>${it.idisk_interactions.map((x) => `<p class="text"><b>${esc(x.drug)}.</b> ${esc(x.note)}</p>`).join("")}<p class="text mlabel">Источник: iDISK 2.0 (данные MSKCC), на английском.</p></details>` : "") +
      (it.idisk_adverse && it.idisk_adverse.length ? `<details><summary>Описанные побочные эффекты по iDISK: ${it.idisk_adverse.length}</summary><p class="text">${it.idisk_adverse.map(esc).join(", ")}</p><p class="text mlabel">Источник: iDISK 2.0 (данные MSKCC), на английском.</p></details>` : "") +
      `<details><summary>Как мы оцениваем</summary>
      <p class="text">Одно исследование может ошибиться, поэтому оценка опирается на обзоры, которые сводят вместе десятки испытаний против плацебо.</p>
      <div class="pyr"><div style="width:46%">Обзоры многих испытаний</div><div style="width:62%">Испытания против плацебо</div><div style="width:78%">Наблюдения за людьми</div><div style="width:94%">Опыты на клетках и животных</div></div>
      <p class="text"><span class="badge b-w">работает</span> обзоры сходятся: эффект есть. <span class="badge b-d">зависит от условий</span> помогает не всем, например только при нехватке. <span class="badge b-n">не доказано</span> только опыты на животных, маленькие испытания или обзоры эффекта не нашли.</p>
      <p class="text">Источник оценки: ${esc(it.origin)}.</p>
    </details>`)}
  </article>`);
}

async function addCard(q) {
  const out = $("#out");
  out.innerHTML = `<div class="card"><p class="empty">Собираем обзоры исследований…</p></div>`;
  try {
    const made = await ACC.createCard(q);
    let c = null;
    try { c = await ACC.card(made.id); } catch (_) {}
    if (!c) { out.innerHTML = `<div class="card"><p class="empty">Не нашли обзоров исследований по «${esc(q)}». Возможно, у вещества другое название: попробуйте латиницей или по действующему веществу.</p></div>`; return; }
    out.innerHTML = newCardHtml(c);
    ACC.mountPeople($("#people"), "card-" + c.id);
    reveal();
  } catch (err) { out.innerHTML = `<div class="card"><p class="empty">${esc(err.message)}</p></div>`; }
}

function newCardHtml(c) {
  const rv = c.reviews || [];
  return `<article class="card story">
    <p class="kicker">Новая карточка</p>
    <h1>${esc(c.name)}</h1>
    <p class="say"><b>${c.verdict ? esc(cap(c.verdict)) + "." : "Ещё не оценено."}</b> Нашли ${c.reviews_total} ${c.reviews_total % 10 === 1 && c.reviews_total % 100 !== 11 ? "обзор" : "обзоров"} исследований${c.verdict ? "" : ", вердикт поставим после проверки"}.</p>
    <section class="sec rv"><h2>Самые цитируемые обзоры</h2>${rv.map((r) => `<p class="src"><a href="${r.doi ? "https://doi.org/" + r.doi : "https://pubmed.ncbi.nlm.nih.gov/" + r.pmid}" target="_blank" rel="noopener">${esc(r.title)}</a> <span class="t">${esc(r.year)} · цитирований: ${r.cited_by}</span></p>`).join("")}</section>
    <section class="sec people" id="people" hidden></section>
  </article>`;
}

function reveal() {
  if (window.EVF) EVF.mount(document.getElementById("out"));
  const els = document.querySelectorAll("#out .rv");
  if (!("IntersectionObserver" in window)) return els.forEach((el) => el.classList.add("in"));
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.1 });
  els.forEach((el) => io.observe(el));
}

function goalHtml(goal) {
  const rows = C.items.filter((it) => it.goals.includes(goal))
    .map((it) => {
      const own = it.effects.filter((e) => e.goals.includes(goal)).sort((a, b) => RANK[a.level] - RANK[b.level]);
      const borrowed = it.verdict === "работает" ? "зависит" : it.verdict;
      return { it, best: own[0] || { text: it.about, level: borrowed } };
    })
    .sort((a, b) => RANK[a.best.level] - RANK[b.best.level] || (GRADE[b.it.grade] || 0) - (GRADE[a.it.grade] || 0));
  const ind = C.items.flatMap((it) => (it.indirect || []).filter((x) => x.goal === goal).map((x) => ({ it, x })))
    .sort((a, b) => RANK[a.x.level] - RANK[b.x.level]);
  const works = rows.filter((r) => r.best.level === "работает").length;
  return `<article class="card">
    <h1>${esc(goal[0].toUpperCase() + goal.slice(1))}</h1>
    <p class="lead">${works ? `Доказано работают: ${works} из ${rows.length}.` : "Надёжно доказанного нет."} Сначала самое надёжное.</p>
    <div class="list">${rows.map(({ it, best }) => `<div class="row" data-q="${esc(it.name)}" tabindex="0" role="button"><div><div class="nm">${esc(it.name)}${ME && !PROFILE.isEmpty(ME) && PROFILE.warningsFor(it, ME).length ? ' <span class="me-dot">осторожно вам</span>' : ""}</div><div class="ef">${esc(best.text)}</div></div><span class="badge b-${LV[best.level]}">${LV_TEXT[best.level]}</span></div>`).join("")}</div>
    ${ind.length ? `<h2>Опосредованно</h2><p class="mlabel">Действуют не напрямую, а через посредника; итог не сильнее самого слабого звена цепочки.</p><div class="list">${ind.map(({ it, x }) => `<div class="row" data-q="${esc(it.name)}" tabindex="0" role="button"><div><div class="nm">${esc(it.name)}</div><div class="ef">${esc(x.via)} → ${esc(goal)}: ${esc(x.text)}. ${esc(x.note)}</div></div><span class="badge b-${LV[x.level]}">${LV_TEXT[x.level]}</span></div>`).join("")}</div>` : ""}
  </article>`;
}

function render(q) {
  const out = $("#out");
  if (q && (CHECK.isUrl(q) || CHECK.looksLikeLabel(q))) {
    document.body.classList.add("has-answer");
    document.title = "Проверка товара: что это по сути";
    CHECK.run(q, out, esc);
    return;
  }
  if (!q) { document.body.classList.remove("has-answer"); out.innerHTML = ""; document.title = "placebo.wiki: работает ли БАД лучше плацебо"; return; }
  document.body.classList.add("has-answer");
  const { items, goal } = find(q);
  const exact = items[0] && score(items[0], norm(q)) >= 80 ? items[0] : null;
  if (exact) { out.innerHTML = cardHtml(exact); document.title = `${exact.name}: работает ли, доза, исследования`; }
  else if (goal) { out.innerHTML = goalHtml(goal); document.title = `БАДы для цели «${goal}» по исследованиям`; }
  else if (items.length) { out.innerHTML = cardHtml(items[0]); document.title = `${items[0].name}: работает ли, доза, исследования`; }
  else {
    const near = nearest(q);
    const chips = (near.length ? near.map((it) => it.name) : ["сон", "стресс", "либидо"]).map((n) => `<a class="chip" href="/?q=${encodeURIComponent(n)}">${esc(n)}</a>`).join("");
    out.innerHTML = `<div class="card"><p class="empty">Пока не знаем «${esc(q)}». ${near.length ? "Возможно, вы искали:" : "Попробуйте цель:"}</p><div class="goal-chips empty-chips">${chips}<a class="chip" href="/b/">Все БАДы</a></div><div class="add" id="add" hidden><button class="add-btn">Создать карточку «${esc(q)}»</button><p class="mlabel">Сайт сам соберёт обзоры исследований, вердикт появится после проверки.</p></div></div>`;
    if (typeof ACC !== "undefined") ACC.ready.then(async (ok) => {
      const a = $("#add");
      if (!ok || !a) return;
      const known = await ACC.findCard(q).catch(() => null);
      if (known) { out.innerHTML = newCardHtml(known); ACC.mountPeople($("#people"), "card-" + known.id); reveal(); return; }
      a.hidden = false;
      a.querySelector("button").onclick = () => addCard(q);
    });
  }
  const people = $("#people");
  if (people && typeof ACC !== "undefined") ACC.mountPeople(people, people.dataset.sid);
  reveal();
  window.scrollTo({ top: 0 });
}

$("#q").addEventListener("input", suggest);
$("#q").addEventListener("keydown", (e) => {
  const btns = [...$("#sugg").querySelectorAll("button")];
  const i = btns.findIndex((b) => b.classList.contains("sel"));
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    if (!btns.length) return;
    const j = (i + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length;
    btns.forEach((b, k) => b.classList.toggle("sel", k === j));
  } else if (e.key === "Escape") $("#sugg").hidden = true;
});
$("#form").onsubmit = (e) => {
  e.preventDefault();
  const sel = $("#sugg").hidden ? null : $("#sugg").querySelector("button.sel");
  const q = sel ? sel.dataset.q : $("#q").value.trim();
  if (q) go(q);
};
$("#sugg").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) go(b.dataset.q); });
$("#out").addEventListener("click", (e) => { const r = e.target.closest(".row"); if (r) go(r.dataset.q); });
$("#out").addEventListener("keydown", (e) => { const r = e.target.closest(".row"); if (r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); go(r.dataset.q); } });
document.addEventListener("click", (e) => { if (!e.target.closest(".field")) $("#sugg").hidden = true; });
for (const id of ["#logo", "#home"]) $(id).onclick = (e) => { e.preventDefault(); history.pushState({}, "", "./"); $("#q").value = ""; morph(() => render("")); $("#q").focus(); };
window.addEventListener("popstate", () => { const q = new URLSearchParams(location.search).get("q") || ""; $("#q").value = q; render(q); });

const human = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1).replace(".", ",") + " млн" : Math.round(n / 1e3) + " тыс.");
function topCol(title, rows) {
  const max = Math.max(...rows.map((r) => r.count));
  return `<section><h3>${title}</h3><ol>${rows.map((r, i) => `<li><button data-q="${esc(r.q)}"><span class="nm">${esc(r.label)}</span><span class="num">${human(r.count)}</span><span class="tq-bar"><i style="width:${(r.count / max) * 100}%;animation-delay:${0.3 + i * 0.08}s"></i></span></button></li>`).join("")}</ol></section>`;
}
fetch("top.json", { cache: "no-cache" }).then((r) => r.json()).then((t) => {
  $("#chips").innerHTML = topCol("Что беспокоит", t.problems) + topCol("Что ищут", t.supplements);
  $("#top-note").textContent = `Запросов в месяц, ${t.source.replace(", 30 дней", "")}`;
}).catch(() => {
  $("#chips").innerHTML = topCol("Частые цели", CHIPS.map((g) => ({ label: g[0].toUpperCase() + g.slice(1), q: g, count: 1 }))).replace(/<span class="num">.*?<\/span>/g, "");
});
const stLeg = $("#st-leg");
if (stLeg) {
  const stBase = stLeg.textContent;
  const pick = (b) => {
    document.querySelectorAll(".st-bar span").forEach((x) => x.classList.toggle("on", x === b));
    stLeg.textContent = b ? b.dataset.t : stBase;
    stLeg.classList.toggle("on", !!b);
  };
  document.querySelectorAll(".st-bar span").forEach((b) => {
    b.addEventListener("mouseenter", () => pick(b));
    b.addEventListener("mouseleave", () => pick(null));
    b.addEventListener("click", () => pick(b.classList.contains("on") ? null : b));
  });
}
$("#chips").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) go(b.dataset.q); });

const startQ = new URLSearchParams(location.search).get("q");
if (startQ) { $("#q").value = startQ; render(startQ); }
