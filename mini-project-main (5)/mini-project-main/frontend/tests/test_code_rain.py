"""Tests for the decorative full-page Code Rain background (code_rain.py)."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import code_rain  # noqa: E402


class CodeRainTests(unittest.TestCase):
    def test_page_script_has_config_and_no_placeholders(self):
        js = code_rain.page_script()
        self.assertNotIn("__CONFIG__", js)
        self.assertIn('"charSet": "01"', js)
        self.assertIn("code-rain-bg", js)

    def test_loader_embeds_script_safely(self):
        h = code_rain.build_html()
        self.assertNotIn("__PAGE_JS__", h)
        self.assertEqual(h.count("</script>"), 1)          # only the loader's own closing tag
        m = re.search(r"var code = (\".*\");\n", h)
        self.assertIsNotNone(m)
        self.assertIn("code-rain-bg", json.loads(m.group(1).replace("<\\/", "</")))

    def test_config_text_cannot_close_the_script_tag(self):
        h = code_rain.build_html({"charSet": "</script><b>"})
        self.assertEqual(h.count("</script>"), 1)

    def test_page_content_is_not_blocked(self):
        js = code_rain.page_script()
        self.assertIn("pointer-events:none", js)
        self.assertIn("z-index:-1", js)

    def test_reduced_motion_is_respected(self):
        self.assertIn("prefers-reduced-motion", code_rain.page_script())

    def test_forbidden_wording_absent(self):
        txt = Path(code_rain.__file__).read_text(encoding="utf-8").lower()
        for w in ("confidence", "accuracy", "certainty", "shap"):
            self.assertIsNone(re.search(r"\b" + w + r"\b", txt), w)


if __name__ == "__main__":
    unittest.main()
