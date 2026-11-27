"""Tests for the full-page title background and the cream/black switch (page_background.py)."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import page_background as PB  # noqa: E402


def _cfg(js):
    m = re.search(r"var C = (\{.*?\}), doc = document", js, re.S)
    return json.loads(m.group(1))


class PageBackgroundTests(unittest.TestCase):
    def test_title_lines_and_palettes(self):
        c = _cfg(PB.page_script())
        self.assertEqual("".join(c["lines"]), "BOTTRAFFICFORECAST")
        self.assertEqual(c["palette"]["bg"], "#FAF6EC")          # light = cream by default
        self.assertEqual(_cfg(PB.page_script(dark=True))["palette"]["bg"], "#000000")

    def test_switch_value_is_validated(self):
        self.assertEqual(_cfg(PB.page_script(switch_to="dark"))["switchTo"], "dark")
        self.assertEqual(_cfg(PB.page_script(switch_to="light"))["switchTo"], "light")
        self.assertIsNone(_cfg(PB.page_script(switch_to="<script>"))["switchTo"])
        self.assertIsNone(_cfg(PB.page_script())["switchTo"])

    def test_no_placeholders_left(self):
        h = PB.build_html()
        self.assertNotIn("__CONFIG__", h)
        self.assertNotIn("__PAGE_JS__", h)

    def test_loader_cannot_be_closed_early(self):
        h = PB.build_html(lines=["</script><b>x"])
        self.assertEqual(h.count("</script>"), 1)

    def test_page_content_is_not_blocked(self):
        js = PB.page_script()
        self.assertIn("pointer-events:none", js)
        self.assertIn("z-index:-1", js)

    def test_title_is_laid_out_in_the_main_area_not_under_the_sidebar(self):
        js = PB.page_script()
        self.assertIn("stMain", js)
        self.assertIn("ResizeObserver", js)

    def test_rain_is_animated_and_respects_reduced_motion(self):
        js = PB.page_script()
        self.assertIn("page-bg-rain", js)
        self.assertIn("requestAnimationFrame", js)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("__pageBgStop", js)                       # old copy is stopped before a new one starts

    def test_rain_colours_follow_the_theme(self):
        self.assertEqual(_cfg(PB.page_script(dark=True))["palette"]["rain"], "#00FF66")
        self.assertNotEqual(_cfg(PB.page_script())["palette"]["rain"], "#00FF66")

    def test_rain_canvas_runs_behind_the_page_and_respects_reduced_motion(self):
        js = PB.page_script()
        self.assertIn("page-bg-rain", js)
        self.assertIn("requestAnimationFrame", js)
        self.assertIn("prefers-reduced-motion", js)
        self.assertEqual(_cfg(js)["charSet"], "01")

    def test_rain_colours_follow_the_theme(self):
        self.assertEqual(_cfg(PB.page_script())["palette"]["rain"], "#2F6B35")
        self.assertEqual(_cfg(PB.page_script(dark=True))["palette"]["rain"], "#00FF66")

    def test_reload_only_when_theme_differs(self):
        js = PB.page_script(switch_to="dark")
        self.assertIn("getItem(key) !== JSON.stringify(want)", js)

    def test_forbidden_wording_absent(self):
        txt = Path(PB.__file__).read_text(encoding="utf-8").lower()
        for w in ("confidence", "accuracy", "certainty", "shap"):
            self.assertIsNone(re.search(r"\b" + w + r"\b", txt), w)


if __name__ == "__main__":
    unittest.main()
