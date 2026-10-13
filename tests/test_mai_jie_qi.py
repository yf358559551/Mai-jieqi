import copy
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "mai-jie-qi"
sys.path.insert(0, str(SKILL / "scripts"))

import card  # noqa: E402
import pairing  # noqa: E402
import solar_term  # noqa: E402

BJT = solar_term.BJT
DEMO = json.loads((ROOT / "examples" / "demo.json").read_text(encoding="utf-8"))
DEMO_NOW = datetime(2026, 10, 24, 12, 0, tzinfo=BJT)

# 不出现在数据、脚本输出和 skill 指令中的功效类措辞（禁用词清单本身除外）
FORBIDDEN = ["养生功效", "调理", "祛湿", "去湿", "滋补", "进补", "润燥", "降火", "去火", "排毒",
             "补气", "养胃", "驱寒", "治疗", "疗效", "暖胃", "健脾"]


class SolarTermTest(unittest.TestCase):
    def test_known_instants(self):
        # 公开历书：2025 冬至 12-21 23:03，2026 立春 02-04 04:02，2026 夏至 06-21 16:24（北京时间）
        cases = [(270, datetime(2025, 12, 21, 23, 3, tzinfo=BJT)),
                 (315, datetime(2026, 2, 4, 4, 2, tzinfo=BJT)),
                 (90, datetime(2026, 6, 21, 16, 24, tzinfo=BJT))]
        for lon, expected in cases:
            got = solar_term.crossing(lon, expected)
            self.assertLess(abs((got - expected).total_seconds()), 30 * 60, (lon, got))

    def test_year_has_24_terms_in_order(self):
        rows = solar_term.year_table(2026)
        self.assertEqual(len(rows), 24)
        self.assertEqual(rows[0]["name"], "小寒")
        self.assertEqual(rows[-1]["name"], "冬至")
        times = [datetime.fromisoformat(r["at"]) for r in rows]
        self.assertEqual(times, sorted(times))

    def test_current_term_today(self):
        info = solar_term.current(datetime(2026, 10, 13, 17, 0, tzinfo=BJT))
        self.assertEqual(info["term"]["name"], "寒露")
        self.assertEqual(info["next"]["name"], "霜降")
        self.assertEqual(info["next"]["days_until"], 10)

    def test_data_complete(self):
        data = solar_term.load_data()
        self.assertEqual(sorted(t["longitude"] for t in data["terms"]), list(range(0, 360, 15)))
        for t in data["terms"]:
            self.assertEqual(len(t["hou"]), 3, t["name"])
            for tag in list(t["prefer"]) + list(t["less"]):
                self.assertTrue(tag in data["tag_phrases"] or tag in ("油炸", "辣"), (t["name"], tag))


class PairingTest(unittest.TestCase):
    def run_demo(self, **override):
        req = copy.deepcopy(DEMO)
        req.update(override)
        return pairing.recommend(req, DEMO_NOW)

    def test_cold_feeling_prefers_warm(self):
        r = self.run_demo()
        self.assertEqual(r["pick"]["id"], "demo-warm-beef")
        self.assertIn("热饮", r["pick"]["matched_tags"])
        self.assertEqual(r["label"], "模拟数据，不可下单")

    def test_hard_constraints(self):
        r = self.run_demo()
        rejected = {x["id"]: x["reasons"] for x in r["rejected"]}
        self.assertIn("含忌口：辣", rejected["demo-spicy"])
        self.assertIn("报价或优惠已过期", rejected["demo-porridge"])

    def test_budget_never_relaxed(self):
        r = self.run_demo(budget_yuan=10)
        self.assertIsNone(r["pick"])
        self.assertTrue(all(any("超出预算" in s for s in x["reasons"]) for x in r["rejected"]
                            if x["id"] in ("demo-warm-beef", "demo-ice-chicken")))

    def test_unknown_kcal_rejected_when_capped(self):
        req = copy.deepcopy(DEMO)
        req["kcal_max"] = 2000
        req["candidates"][0]["items"][0]["kcal"] = None
        r = pairing.recommend(req, DEMO_NOW)
        ids = {x["id"] for x in r["rejected"]}
        self.assertIn("demo-warm-beef", ids)

    def test_unverified_quote_rejected(self):
        req = copy.deepcopy(DEMO)
        req["candidates"][0]["quote"]["verified"] = False
        r = pairing.recommend(req, DEMO_NOW)
        self.assertNotEqual(r["pick"]["id"], "demo-warm-beef")

    def test_summer_term_flips_ranking(self):
        r = self.run_demo(term="大暑", feelings=["怕热"])
        self.assertEqual(r["pick"]["id"], "demo-ice-chicken")

    def test_expired_activity_gives_no_bonus(self):
        req = copy.deepcopy(DEMO)
        req["candidates"][1]["activity"]["ends_at"] = (DEMO_NOW - timedelta(hours=1)).isoformat()
        r = pairing.recommend(req, DEMO_NOW)
        alt = [a for a in r["alternatives"] if a["id"] == "demo-ice-chicken"][0]
        self.assertIsNone(alt["activity"])

    def test_unknown_feeling_reported(self):
        r = self.run_demo(feelings=["怕冷", "上火"])
        self.assertEqual(r["feelings_unknown"], ["上火"])

    def test_demo_now_requires_demo(self):
        req = copy.deepcopy(DEMO)
        req["demo"] = False
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "real.json"
            tmp.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(SystemExit):
                pairing.main([str(tmp), "--demo-now", DEMO_NOW.isoformat()])


class OutputTest(unittest.TestCase):
    def test_card_is_valid_svg_with_watermark(self):
        r = pairing.recommend(copy.deepcopy(DEMO), DEMO_NOW)
        svg = card.render(r)
        ET.fromstring(svg)
        self.assertIn("模拟数据", svg)
        self.assertIn("霜降", svg)

    def test_no_efficacy_wording(self):
        texts = [(SKILL / "data" / "solar_terms.json").read_text(encoding="utf-8"),
                 pairing.to_markdown(pairing.recommend(copy.deepcopy(DEMO), DEMO_NOW))]
        skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        texts.append(re.sub(r"<!-- forbidden-start -->.*?<!-- forbidden-end -->", "", skill_md, flags=re.S))
        for text in texts:
            for word in FORBIDDEN:
                self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
