"""Tests for the classic matrix-style banner (hero_banner.py)."""
import os
import re
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hero_banner  # noqa: E402


class HeroBannerTests(unittest.TestCase):
    def test_html_has_canvas_and_config(self):
        h = hero_banner.build_html()
        self.assertIn("<canvas", h)
        self.assertNotIn("__CONFIG__", h)
        self.assertNotIn("__HEIGHT__", h)
        self.assertIn('"title": "BOT TRAFFIC FORECAST"', h)
        self.assertIn('"charSet": "01"', h)

    def test_config_text_cannot_close_the_script_tag(self):
        h = hero_banner.build_html({"title": "</script><b>x"})
        self.assertEqual(h.count("</script>"), 1)

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion", hero_banner.build_html())

    def test_forbidden_wording_absent(self):
        txt = Path(hero_banner.__file__).read_text(encoding="utf-8").lower()
        for w in ("confidence", "accuracy", "certainty", "shap"):
            self.assertIsNone(re.search(r"\b" + w + r"\b", txt), w)

    # ---- the clear version: what makes the letters readable
    def test_the_title_is_real_text_not_digits_in_a_grid(self):
        h = hero_banner.build_html()
        self.assertIn("ctx.fillText(ln.chars[k].ch", h)               # letters are drawn as text, one by one
        self.assertIn("strokeText", h)                                # with a thin dark edge so they stay crisp
        self.assertNotIn("getImageData", h)                           # the old version sampled the title into a digit grid
        self.assertNotIn("sampleGrid", h)

    def test_the_title_is_measured_and_always_fits(self):
        h = hero_banner.build_html()
        self.assertIn("measureText", h)
        self.assertIn("W * 0.86", h)                                  # at most 86% of the banner width
        self.assertIn('["BOT TRAFFIC", "FORECAST"]', h)               # two lines on narrow screens

    def test_no_digits_are_drawn_behind_the_title_or_on_the_frame(self):
        h = hero_banner.build_html()
        self.assertIn("plate[i] = e < 0.9 ? 0", h)                    # an empty ellipse around the title
        self.assertIn("< 18", h)                                      # and an empty margin around the frame lines

    def test_the_texture_stays_faint_and_sparse(self):
        c = hero_banner.CONFIG
        self.assertLessEqual(c["fill"], 30)                           # share of background cells that show a digit
        self.assertLessEqual(c["rainDensity"], 15)                    # share of columns with a falling trail
        self.assertLessEqual(c["height"], 200)
        self.assertIn("Math.round(cs * 0.9)", hero_banner.build_html())   # a digit is never bigger than its cell
        self.assertNotIn("subtitle", c)                               # no extra line of text near the digits

    def test_render_draws_the_banner_in_an_iframe(self):
        calls = []
        fake = types.ModuleType("streamlit")
        fake.iframe = lambda html, **kw: calls.append((html, kw))
        sys.modules["streamlit"] = fake
        try:
            hero_banner.render()
        finally:
            del sys.modules["streamlit"]
        self.assertEqual(calls, [(hero_banner.build_html(), {"height": hero_banner.CONFIG["height"] + 4})])


if __name__ == "__main__":
    unittest.main()
