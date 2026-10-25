# placebo.wiki

**Работает ли БАД лучше плацебо?** Поисковик по 134 добавкам: вердикт по обзорам исследований, дозы, верхние пределы, формы, мифы, взаимодействия и ссылки на статьи. Сайт: https://placebo.wiki

**Does a supplement beat placebo?** A search engine over 134 supplements (Russian UI): evidence verdicts from systematic reviews and meta-analyses, doses, upper limits, forms, myths, drug interactions and linked studies.

## Что внутри / What's inside
- `site/`: статический сайт (поиск, проверка товара по ссылке Wildberries или составу, 148 страниц для поиска).
- `data/catalog.json`: база в открытом виде / the open dataset.
- `data/open/`: открытая база исследований о БАДах (Parquet): статьи, мета-анализы, испытания из реестра, жалобы на вред, с уровнем доказательности; описание в `data/open/README.md`, сборщик в `data/pipeline/harvest/` / the open evidence base.
- `mcp/server.py`: MCP-сервер для агентов (`search`, `get_supplement`, `by_goal`, `list_goals`).
- `docs/formula.md`: правила, по которым пишутся тексты (сила слова = надёжность данных по GRADE), и `data/seo/verify.py`, который их проверяет.

## Запуск / Run
```
python3 -m http.server 8791 --directory site
claude mcp add placebo -- uv run --script mcp/server.py
```

## Данные / Data
Основа: Brain 25 Evidence (MIT). Подробно: `NOTICE.md`. Не является медицинской рекомендацией / Not medical advice.

## Лицензия / License
MIT
