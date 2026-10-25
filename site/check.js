// Product check: a Wildberries link or a pasted label -> which substances it really contains and whether doses match the studies.
const CHECK = (() => {
  const UNIT = { "мг": "mg", "mg": "mg", "мкг": "mcg", "mcg": "mcg", "µg": "mcg", "г": "g", "g": "g", "ме": "iu", "iu": "iu", "me": "iu" };
  const TO_MG = { mg: 1, mcg: 0.001, g: 1000 };
  const MARKETING = ["детокс", "очищ", "чистк", "шлак", "сжигател", "жиросжиг", "уникальн", "мгновенн", "омолож", "ультра", "супер", "100%", "лечит"];
  const DOSE_RE = /(\d+(?:[.,]\d+)?)\s*(мкг|мг|mcg|mg|µg|ме|iu|г|g)(?![a-zа-я])/i;

  const isUrl = (s) => /^https?:\/\//i.test(s.trim()) || /(wildberries|wb\.ru|ozon\.ru|market\.yandex)/i.test(s);
  const looksLikeLabel = (s) => s.length > 60 || /состав|ингредиент|в 1 капсул|в 1 таблет|содержит/i.test(s);

  function num(s) { return parseFloat(String(s).replace(",", ".")); }
  function unitOf(u) { return UNIT[u.toLowerCase()] || null; }

  function parseRange(text) {
    const m = String(text || "").match(/(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(мкг|мг|г|МЕ|mg|mcg|IU)/i)
      || String(text || "").match(/(\d+(?:[.,]\d+)?)()\s*(мкг|мг|г|МЕ|mg|mcg|IU)/i);
    if (!m) return null;
    const u = unitOf(m[3]);
    return { min: num(m[1]), max: m[2] ? num(m[2]) : num(m[1]), unit: u };
  }

  function sameUnit(a, b) {
    if (a.unit === b.unit) return [a.value, b];
    if (TO_MG[a.unit] && TO_MG[b.unit]) return [a.value * TO_MG[a.unit] / TO_MG[b.unit], b];
    return null;
  }

  function findIngredients(text) {
    const t = " " + text.toLowerCase().replace(/ё/g, "е") + " ";
    const mentions = [];
    for (const it of window.CATALOG.items) {
      const names = [it.name, ...it.aliases].map((n) => n.toLowerCase().replace(/ё/g, "е")).filter((n) => n.length > 2 || /\d/.test(n));
      for (const n of names) {
        const re = new RegExp("(^|[^a-zа-я0-9])(" + n.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&") + ")", "gi");
        for (const m of t.matchAll(re)) mentions.push({ it, pos: m.index + m[1].length, end: m.index + m[0].length });
      }
    }
    mentions.sort((x, y) => x.pos - y.pos);
    const byItem = new Map();
    for (const m of mentions) if (!byItem.has(m.it.id)) byItem.set(m.it.id, { it: m.it, pos: m.pos, doses: [] });
    for (const d of t.matchAll(new RegExp(DOSE_RE, "gi"))) {
      let k = mentions.findLastIndex((m) => m.end <= d.index);
      if (k < 0 || d.index - mentions[k].end > 60) continue;
      // «магний B6 400 мг»: a dose after a tight cluster of names belongs to the first name of the cluster.
      while (k > 0 && mentions[k].pos - mentions[k - 1].end < 4 && mentions[k - 1].it.id !== mentions[k].it.id) k--;
      const ctx = t.slice(Math.max(0, d.index - 40), d.index + d[0].length + 20);
      byItem.get(mentions[k].it.id).doses.push({ value: num(d[1]), unit: unitOf(d[2]), raw: d[0].trim(), daily: /суточн|в сутки|в день|\/сут/.test(ctx) });
    }
    return [...byItem.values()].sort((x, y) => x.pos - y.pos).map(({ it, pos, doses }) => ({
      it, pos,
      // A stated daily dose wins; otherwise a salt is labelled by its weight first and the element after it, so the smaller same-unit dose is the element.
      dose: !doses.length ? null : doses.find((x) => x.daily) || doses.reduce((x, y) => (x.unit === y.unit && y.value < x.value ? y : x)),
    }));
  }

  function doseVerdict(it, dose) {
    if (!dose) return { text: "Доза в описании не указана", cls: "n" };
    const range = parseRange(it.dosage);
    const limit = parseRange(it.upper_limit);
    if (limit && limit.unit) {
      const c = sameUnit(dose, limit);
      if (c && c[0] > limit.max) return { text: `${dose.raw}: выше верхнего предела (${limit.max} ${limit.unit === "mg" ? "мг" : limit.unit === "mcg" ? "мкг" : limit.unit === "iu" ? "МЕ" : "г"})`, cls: "bad" };
    }
    if (range && range.unit) {
      const c = sameUnit(dose, range);
      if (c) {
        if (c[0] < range.min) return { text: `${dose.raw}: меньше, чем в испытаниях (${it.dosage})`, cls: "d" };
        if (c[0] > range.max) return { text: `${dose.raw}: больше, чем в испытаниях (${it.dosage})`, cls: "d" };
        return { text: `${dose.raw}: как в испытаниях`, cls: "w" };
      }
    }
    return { text: range ? `${dose.raw}; в испытаниях: ${it.dosage}` : `${dose.raw}; доза из испытаний в базе не указана`, cls: "n" };
  }

  async function fetchWB(url) {
    const m = url.match(/catalog\/(\d+)/) || url.match(/(\d{6,})/);
    if (!m) throw new Error("Не нашёл номер товара в ссылке.");
    const nm = Number(m[1]);
    const vol = Math.floor(nm / 1e5), part = Math.floor(nm / 1e3);
    const tries = Array.from({ length: 40 }, (_, i) => {
      const b = String(i + 1).padStart(2, "0");
      return fetch(`https://basket-${b}.wbbasket.ru/vol${vol}/part${part}/${nm}/info/ru/card.json`).then((r) => (r.ok ? r.json() : Promise.reject()));
    });
    const card = await Promise.any(tries).catch(() => null);
    if (!card) throw new Error("Wildberries не отдал карточку товара.");
    const opts = (card.options || []).map((o) => `${o.name}: ${o.value}`).join("\n");
    return { title: card.imt_name || "Товар Wildberries", text: [card.imt_name, opts, card.description].filter(Boolean).join("\n") };
  }

  function report(title, text, esc) {
    const items = findIngredients(text);
    const low = text.toLowerCase();
    const promises = MARKETING.filter((w) => low.includes(w));
    const LVT = { "работает": "работает", "зависит": "зависит от условий", "не подтверждено": "не доказано" };
    const LV = { "работает": "w", "зависит": "d", "не подтверждено": "n" };
    const essence = items.length ? items.map((f) => f.it.name.toLowerCase() + (f.dose ? " " + f.dose.raw : "")).join(" + ") : null;
    return `<article class="card check">
      <h1>${esc(title)}</h1>
      <p class="lead">${essence ? `По сути это: <b>${esc(essence)}</b>.` : "Знакомых нам веществ в описании не нашлось. Вставьте состав с упаковки целиком."}</p>
      ${items.length ? `<h2>Что внутри</h2>${items.map(({ it, dose }) => { const d = doseVerdict(it, dose); return `
        <div class="eff"><div><a href="?q=${encodeURIComponent(it.name)}"><b>${esc(it.name)}</b></a><div class="ef dose dose-${d.cls}">${esc(d.text)}</div></div>
        <span class="badge b-${LV[it.verdict]}">${LVT[it.verdict]}</span></div>`; }).join("")}` : ""}
      ${promises.length ? `<h2>Обещания из рекламы</h2><p class="text">В описании есть слова «${promises.map(esc).join("», «")}». Исследованиями такие обещания обычно не подтверждены.</p>` : ""}
      <p class="text mlabel">Разбор по описанию продавца: проверьте состав на упаковке. Название на витрине ничего не говорит о пользе, важны вещество, форма и доза.</p>
    </article>`;
  }

  async function run(input, out, esc) {
    out.innerHTML = `<p class="empty">Разбираю…</p>`;
    try {
      if (isUrl(input)) {
        if (!/wildberries|wb\.ru/i.test(input)) {
          out.innerHTML = `<p class="empty">Пока читаем ссылки только с Wildberries. Для Ozon и Маркета скопируйте состав с карточки товара и вставьте сюда.</p>`;
          return;
        }
        const { title, text } = await fetchWB(input);
        out.innerHTML = report(title, text, esc);
      } else {
        out.innerHTML = report("Разбор состава", input, esc);
      }
    } catch (e) {
      out.innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    }
  }

  return { isUrl, looksLikeLabel, run, findIngredients, doseVerdict };
})();
