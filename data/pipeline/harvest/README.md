# Сбор в общую базу

Программы по API складывают всё найденное о каждом веществе из каталога в `data/base/base.sqlite`. ИИ не участвует.

```
python3 data/pipeline/harvest/run.py                       # все вещества, все источники, по 100 с каждого
python3 data/pipeline/harvest/run.py --only kreatin --limit 1000
python3 -m unittest discover data/pipeline/harvest
```

| Источник | Что даёт | Уровень берётся из |
|---|---|---|
| europepmc | статьи PubMed и европейских баз с аннотациями: все мета-анализы и РКИ, остальное по --limit самых цитируемых | типа публикации и MeSH |
| clinicaltrials | реестр испытаний целиком | дизайна (рандомизация, наблюдение) |
| openfda | жалобы на вред после продуктов (FDA CAERS) | всегда «описание случаев» |
| cyberleninka | русские журналы | не определяется |
| reddit | рассказы людей из r/Supplements, r/Nootropics, r/Biohackers через архив Arctic Shift (сам reddit.com отвечает 403) | «опыт людей» |
| youtube, ozon, wildberries, yandex_market, telegram | заглушки | |

- Повторный запуск добавляет только новое; одна статья из двух источников хранится один раз, второй источник пишется в `also_in`.
- Названия для поиска: `names.json`, у вещества список (первое главное, дальше синонимы: cholecalciferol для витамина D). Статья берётся, если название есть в заголовке или в аннотации стоит «<название> supplementation / supplement / intake»: голое название в аннотации тащит лабораторные маркеры вроде creatine kinase. Новое вещество: `python3 names.py`.
- Где источник не даёт тип работы (КиберЛенинка, часть статей), уровень ставится по словам заголовка и аннотации (`levels.py`), в `extra` пометка `level_by: keywords`. Старые записи: `run.py --relevel`.
- Параллельный сбор в другой файл и слияние: `run.py --db other.sqlite`, затем `run.py --merge other.sqlite`.
- Сбои уходят в Telegram, если заданы `PLACEBO_TG_TOKEN` и `PLACEBO_TG_CHAT`, иначе в `data/base/alerts.log`.
- У статей Europe PMC в `extra`: `retracted` (статья отозвана), `intake` (речь о приёме вещества, а не о молекуле в организме).
