"""Tests for the Phase 4 About page text and render function. Run from frontend/:  python -m unittest discover -s tests -v"""
import sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api_client as api
import ui_text as T

FORBIDDEN = ("confidence", "certainty", "shap", "attack detected", "real-time detection", "guarantee that traffic is safe")


def all_text():
    parts = [T.ABOUT_TITLE, T.ABOUT_INTRO, T.ABOUT_METRICS_NOTE, T.ABOUT_LOW_RECALL] + T.ABOUT_HOW + T.ABOUT_LIMITATIONS
    parts += [x for row in T.ABOUT_FEATURES + T.ABOUT_STATES + T.ABOUT_METRICS for x in row]
    return " ".join(parts).lower()


class Text(unittest.TestCase):
    def test_nav(self):
        self.assertEqual(T.NAV_PAGES, [T.NAV_FORECAST, T.NAV_ABOUT])

    def test_no_forbidden_wording(self):
        for w in FORBIDDEN:
            self.assertNotIn(w, all_text())

    def test_features_match_backend_order(self):
        self.assertEqual([f for f, _ in T.ABOUT_FEATURES], api.FEATURES)

    def test_states_match_thresholds(self):
        self.assertEqual([s for s, _ in T.ABOUT_STATES], list(api.STATES))

    def test_low_recall_is_stated(self):
        low = [r for r in T.ABOUT_METRICS if r[0].startswith("Low state recall")][0]
        self.assertEqual(low[1], "0.00% (0 of 23)")
        self.assertIn("does not rule out Low", T.ABOUT_LOW_RECALL)

    def test_metrics_match_report(self):
        report = Path(__file__).resolve().parents[2] / "docs" / "FINAL_REPORT_MEMBER3.md"
        if not report.exists():
            self.skipTest("docs/FINAL_REPORT_MEMBER3.md not found")
        text = report.read_text(encoding="utf-8")
        for value in ("6.9211", "9.3123", "8.4283", "11.6736", "0.6216", "0.2741", "71.57%", "59.80%", "92.31%", "61.54%",
                      "92.42%", "74.24%", "17.39%"):
            self.assertIn(value, text)
        for _, lstm, base in T.ABOUT_METRICS[:3]:
            self.assertTrue(float(lstm) < 100 and float(base) < 100)


class Render(unittest.TestCase):
    def test_render_runs_with_fake_streamlit(self):
        fake = mock.MagicMock()
        fake.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
        sys.modules.pop("about_page", None)
        with mock.patch.dict(sys.modules, {"streamlit": fake}):
            import about_page
            about_page.render()
        sys.modules.pop("about_page", None)          # so a later import uses the real streamlit
        fake.header.assert_called_once_with(T.ABOUT_TITLE)
        self.assertEqual(fake.tabs.call_count, 1)
        self.assertGreaterEqual(fake.dataframe.call_count, 3)


if __name__ == "__main__":
    unittest.main()
