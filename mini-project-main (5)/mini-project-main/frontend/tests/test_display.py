"""Tests for display.py. Run from frontend/:  python -m unittest discover -s tests -v"""
import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import api_client as api
import display as D

FC = {"predicted_bot_pct_next_minute": 34.85, "predicted_state": "Medium", "model_status": "PROVISIONAL",
      "seed_predictions": {"46": 34.45, "42": 33.1, "44": 37.2, "43": 34.5, "45": 35.0}, "seed_spread_pct_points": 4.1}
WIN = pd.DataFrame({"Bot_Pct": [18.0, 19.0, 17.0, 18.0, 18.0]})


class States(unittest.TestCase):
    def test_all_states_and_unknown(self):
        for s in api.STATES:
            self.assertIn("accent", D.state_view(s))
        with self.assertRaises(ValueError):
            D.state_view("Critical")

    def test_card_shows_backend_state_and_pct(self):
        h = D.card_html(FC)
        self.assertIn("34.85 %", h); self.assertIn("MEDIUM", h); self.assertNotIn("[MOCK]", h); self.assertNotIn("\n", h)

    def test_card_mock_tag(self):
        self.assertEqual(D.card_html(api.MOCK_FORECAST_RESPONSE, placeholder=True).count("[MOCK]"), 2)

    def test_no_forbidden_words(self):
        text = (D.card_html(FC) + D.gauge_html(4.1)).lower()
        for w in ("confidence", "certainty", "shap", "real-time", "attack detected"):
            self.assertNotIn(w, text)


class Disagreement(unittest.TestCase):
    def test_boundaries(self):
        got = [D.disagreement_level(x)["level"] for x in (0, 5.0, 5.01, 10.0, 10.01)]
        self.assertEqual(got, ["Low", "Low", "Moderate", "Moderate", "High"])

    def test_gauge_position_clamped(self):
        self.assertEqual((D.gauge_position(-3), D.gauge_position(7.5), D.gauge_position(99)), (0.0, 50.0, 100.0))


class Series(unittest.TestCase):
    def test_seed_order(self):
        s = D.seed_series(FC)
        self.assertEqual(list(s.index), [f"Seed {k}" for k in range(42, 47)])
        self.assertEqual(s["Seed 44"], 37.2)


class Chart(unittest.TestCase):
    def test_frame_shape_and_alignment(self):
        f = D.observed_vs_forecast_frame(WIN, 34.85)
        self.assertEqual(list(f.index), [-4, -3, -2, -1, 0, 1])
        obs, fc = f.iloc[:, 0], f.iloc[:, 1]
        self.assertTrue(math.isnan(obs.loc[1]))                 # no observation at t+1
        self.assertEqual(fc.loc[0], 18.0); self.assertEqual(fc.loc[1], 34.85)
        self.assertTrue(all(math.isnan(fc.loc[i]) for i in (-4, -3, -2, -1)))
        self.assertTrue((f["Medium starts (25%)"] == 25).all() and (f["High starts (50%)"] == 50).all())


class Describe(unittest.TestCase):
    def test_statements(self):
        a, b, c = D.describe_forecast(WIN, {**FC, "seed_spread_pct_points": 4.1})
        self.assertIn("steady", a); self.assertIn("16.9 points above", b); self.assertIn("low disagreement", c)

    def test_rising_and_below(self):
        w = pd.DataFrame({"Bot_Pct": [10.0, 20, 30, 40, 50]})
        a, b, _ = D.describe_forecast(w, {**FC, "predicted_bot_pct_next_minute": 40.0})
        self.assertIn("rose", a); self.assertIn("10.0 points below", b)


if __name__ == "__main__":
    unittest.main()
