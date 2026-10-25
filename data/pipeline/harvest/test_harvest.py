import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import base  # noqa: E402
from sources.clinicaltrials import level as ct_level  # noqa: E402
from sources.europepmc import level, query  # noqa: E402
import levels  # noqa: E402
from run import relevel  # noqa: E402


def finding(source, sid, **kw):
    return {"source": source, "source_id": sid, "kind": "science", "level": "unknown", **kw}


class Levels(unittest.TestCase):
    def test_europepmc(self):
        self.assertEqual(level(["Meta-Analysis", "Journal Article"], ["Humans"]), "meta")
        self.assertEqual(level(["Randomized Controlled Trial"], ["Humans"]), "rct")
        self.assertEqual(level(["Clinical Trial, Phase II"], []), "trial")
        self.assertEqual(level(["Journal Article", "case-report"], ["Humans"]), "case")
        self.assertEqual(level(["Journal Article"], ["Animals", "Humans", "Mice", "Disease Models, Animal"]), "animal_cell")
        self.assertEqual(level(["Journal Article"], ["Humans", "Cohort Studies"]), "cohort")
        self.assertEqual(level(["Review"], ["Humans"]), "review")
        self.assertEqual(level(["Journal Article"], ["Humans"]), "unknown")

    def test_clinicaltrials(self):
        self.assertEqual(ct_level({"studyType": "INTERVENTIONAL", "designInfo": {"allocation": "RANDOMIZED"}}), "rct")
        self.assertEqual(ct_level({"studyType": "INTERVENTIONAL"}), "trial")
        self.assertEqual(ct_level({"studyType": "OBSERVATIONAL"}), "observational")


class Keywords(unittest.TestCase):
    def test_strongest_design_wins(self):
        self.assertEqual(levels.guess("A meta-analysis of randomized trials", ""), "meta")
        self.assertEqual(levels.guess("Creatine in a randomized, double-blind, placebo-controlled trial", ""), "rct")
        self.assertEqual(levels.guess("Effect of creatine in rats", "in vitro data"), "animal_cell")
        self.assertEqual(levels.guess("Креатин: систематический обзор", ""), "meta")
        self.assertEqual(levels.guess("Влияние на крыс", ""), "animal_cell")
        self.assertIsNone(levels.guess("Creatine and sleep", ""))

    def test_relevel_marks_the_guess(self):
        r = finding("cyberleninka", "x", title="Рандомизированное плацебо-контролируемое исследование")
        relevel(r)
        self.assertEqual((r["level"], r["extra"]["level_by"]), ("rct", "keywords"))
        r = finding("europepmc", "y", level="review", title="randomized trial")
        relevel(r)
        self.assertEqual(r["level"], "review")


class Query(unittest.TestCase):
    def test_synonyms_and_intake_phrases(self):
        q = query(["vitamin D", "cholecalciferol"])
        self.assertIn('TITLE:"cholecalciferol"', q)
        self.assertIn('ABSTRACT:"vitamin D supplementation"', q)
        self.assertNotIn('ABSTRACT:"vitamin D" ', q)


class Store(unittest.TestCase):
    def setUp(self):
        self.db = base.connect(":memory:")

    def test_same_paper_from_two_sources_is_one_row(self):
        self.assertTrue(base.add(self.db, "kreatin", finding("europepmc", "1", doi="10.1/x")))
        self.assertFalse(base.add(self.db, "kreatin", finding("openalex", "W9", doi="10.1/x")))
        rows = self.db.execute("select source, also_in from findings").fetchall()
        self.assertEqual(rows, [("europepmc", '["openalex"]')])

    def test_rerun_adds_nothing(self):
        base.add(self.db, "kreatin", finding("reddit", "a"))
        self.assertFalse(base.add(self.db, "kreatin", finding("reddit", "a")))

    def test_same_paper_counts_for_each_substance(self):
        self.assertTrue(base.add(self.db, "kreatin", finding("europepmc", "1", pmid="1")))
        self.assertTrue(base.add(self.db, "magniy", finding("europepmc", "1", pmid="1")))

    def test_unknown_level_is_refused(self):
        with self.assertRaises(AssertionError):
            base.add(self.db, "kreatin", finding("europepmc", "1", level="guess"))


if __name__ == "__main__":
    unittest.main()
