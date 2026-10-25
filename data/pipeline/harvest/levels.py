from __future__ import annotations

"""Evidence level from the words of the title and abstract, for findings whose source gives no publication type.

Rules go from the strongest design down; the first match wins. The result is marked level_by=keywords in extra.
"""
import re

RULES = [
    ("meta", r"meta-?analy|systematic review|мета-?анализ|систематическ\w* обзор"),
    ("rct", r"randomi[sz]ed\W+(\w+\W+){0,3}(trial|study)|placebo-controlled|рандомизир\w*|плацебо-?контрол"),
    ("animal_cell", r"\b(rats?|mice|mouse|murine|in vitro|cell lines?|zebrafish)\b|крыс|мыш(ей|ах|и)\b|in vitro|культур\w* клеток|у животных"),
    ("trial", r"\b(clinical trial|open-label|pilot study|intervention study)\b|клиническ\w* исследован|открыт\w* исследован"),
    ("cohort", r"\b(cohort|prospective study|longitudinal study)\b|когорт|проспективн"),
    ("case_control", r"case-control|случай-контроль"),
    ("cross_sectional", r"cross-sectional|поперечн\w* исследован|одномоментн"),
    ("case", r"\bcase report\b|клиническ\w* случа|случай из практики|описание случая"),
    ("review", r"\breview\b|обзор"),
]
COMPILED = [(level, re.compile(rx, re.I)) for level, rx in RULES]


def guess(title: str | None, text: str | None) -> str | None:
    s = f"{title or ''} {text or ''}"
    return next((level for level, rx in COMPILED if rx.search(s)), None)
