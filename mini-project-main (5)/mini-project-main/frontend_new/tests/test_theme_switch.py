"""Tests for the cream / black page switch (theme_switch.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import theme_switch as TS  # noqa: E402


class ThemeSwitchTests(unittest.TestCase):
    def test_nothing_to_do_without_a_valid_switch(self):
        for bad in (None, "", "blue", "<script>"):
            self.assertIsNone(TS.page_script(bad))
            self.assertIsNone(TS.build_html(bad))

    def test_dark_and_light_values(self):
        self.assertIn('var want = "Dark"', TS.page_script("dark"))
        self.assertIn('var want = "Light"', TS.page_script("light"))

    def test_reloads_only_when_the_theme_differs(self):
        self.assertIn("getItem(key) !== JSON.stringify(want)", TS.page_script("dark"))

    def test_loader_is_well_formed(self):
        h = TS.build_html("dark")
        self.assertNotIn("__PAGE_JS__", h)
        self.assertNotIn("__WANT__", h)
        self.assertEqual(h.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()
