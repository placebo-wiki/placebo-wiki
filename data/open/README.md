# placebo.wiki: studies on dietary supplements

166 594 findings about 134 dietary supplements, collected automatically from open sources and labelled with an
evidence level (meta-analysis, RCT, cohort, case report, animal study...). Collected 2026-10-25. Built for
[placebo.wiki](https://placebo.wiki), a Russian-language site that checks whether supplements work better than placebo.

Открытая база placebo.wiki: исследования о БАДах из открытых источников с уровнем доказательности. Собрана автоматически,
людьми не прочитана: вердикты на сайте стоят только на отобранных сильнейших работах.

## Sources

| source | findings |
|---|---:|
| europepmc | 79 698 |
| clinicaltrials | 66 925 |
| cyberleninka | 12 053 |
| openfda | 6 105 |
| reddit | 1 813 |

- europepmc: Europe PMC (PubMed and European sources); all meta-analyses and RCTs plus the most cited other papers per substance.
- clinicaltrials: ClinicalTrials.gov registry, all registrations per substance.
- openfda: FDA CAERS reports of harm after food and supplement products.
- cyberleninka: Russian-language journals.
- reddit: posts in r/Supplements, r/Nootropics, r/Biohackers via the Arctic Shift archive.

## Evidence levels

| level | findings |
|---|---:|
| rct (РКИ) | 93 022 |
| meta (Мета-анализ, систематический обзор) | 17 824 |
| trial (Испытание без рандомизации) | 16 657 |
| unknown (Не определено) | 13 951 |
| animal_cell (Животные, клетки) | 7 690 |
| case (Описание случаев) | 6 283 |
| observational (Наблюдательное) | 5 808 |
| review (Нарративный обзор) | 3 187 |
| people (Опыт людей) | 1 813 |
| cohort (Когортное) | 229 |
| case_control (Случай-контроль) | 77 |
| cross_sectional (Поперечное) | 53 |

The level comes from the source's own publication type and MeSH terms; where the source gives none, from words in the
title and abstract (`level_by_keywords = true`). `zone`: cause (meta-analysis, RCT), link (observational designs),
hypothesis (case reports, animal and cell studies, narrative reviews, people's posts).

## Columns

`findings`: id, source, source_id, kind (science, registry, safety, people), level, level_label, zone, substance
(id in `substances`), title, text, text_license, url, published, authors, journal, doi, pmid, lang, cited_by,
retracted, about_intake (the paper is about taking the substance, not the molecule in the body), level_by_keywords,
also_in (other sources that returned the same paper), fetched_at.

`substances`: id, name_ru, names_en (search names), verdict on placebo.wiki.

## Licenses

Full text is included for 89 614 findings, only where redistribution is allowed:

- ClinicalTrials.gov and openFDA: US government works, public domain.
- Europe PMC open-access articles: the abstract under the article's own license (see the article).
- Paywalled Europe PMC abstracts belong to their publishers, CyberLeninka licenses differ per article: text omitted,
  title, authors, journal and link kept.
- Reddit posts belong to their authors: only link, date, community and score kept.

Labels, levels and the compilation: CC BY 4.0, credit placebo.wiki.

## Caveats

- Not medical advice. Levels are assigned by code, not by people; a paper can be mislabelled.
- Search is by substance names in titles and by phrases like "<name> supplementation" in abstracts: papers that name the
  substance differently are missed, and papers about the body's own molecule can slip in (see `about_intake`).
- Collection code: https://github.com/placebo-wiki/placebo-wiki (data/pipeline/harvest).
