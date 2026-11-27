"""Tests for tests/backend_check.py using the stand-in backend (real validator + contract example).
Run from the frontend/ folder:   python -m unittest discover -s tests -v"""
import copy, sys, threading, unittest
from pathlib import Path

FRONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONT)); sys.path.insert(0, str(FRONT / "tests"))
import backend_check as BC
import test_api_client as TA

READY = bool(TA.DOC and TA.VALIDATE)
by_name = lambda results: {n: (s, d) for n, s, d in results}
CODES = ["MISSING_FEATURES", "BAD_TIMESTAMP", "NOT_CONSECUTIVE", "BAD_SHAPE", "NAN_OR_INF", "NEGATIVE_VALUE", "BOT_PCT_RANGE"]


class Compare(unittest.TestCase):
    base = {"forecast_horizon_minutes": 1, "predicted_bot_pct_next_minute": 19.1234, "predicted_state": "Low",
            "state_thresholds": {"Low": "<25", "Medium": "25-<50", "High": ">=50"},
            "seed_predictions": {"42": 18.9, "43": 19.3, "44": 18.7, "45": 19.4, "46": 19.2}, "seed_spread_pct_points": 0.7,
            "model_version": "v1", "model_status": "PROVISIONAL", "warnings": ["w1"]}

    def test_identical_and_tiny_float_noise(self):
        self.assertEqual(BC.compare_forecasts(self.base, copy.deepcopy(self.base)), [])
        noisy = copy.deepcopy(self.base); noisy["predicted_bot_pct_next_minute"] += 0.0004
        self.assertEqual(BC.compare_forecasts(noisy, self.base), [])

    def test_every_kind_of_difference_is_reported(self):
        for field, change in [("predicted_bot_pct_next_minute", 19.2), ("predicted_state", "High"), ("model_version", "v2"),
                              ("model_status", "MOCK"), ("seed_spread_pct_points", 3.0), ("warnings", []),
                              ("seed_predictions", {"42": 1.0})]:
            with self.subTest(field=field):
                other = copy.deepcopy(self.base); other[field] = change
                self.assertTrue(BC.compare_forecasts(other, self.base), field)
        other = copy.deepcopy(self.base); other["seed_predictions"]["44"] = 25.0
        self.assertIn("seed 44", BC.compare_forecasts(other, self.base)[0])

    def test_extra_backend_warnings_are_fine(self):
        other = copy.deepcopy(self.base); other["warnings"] = ["w1", "extra"]
        self.assertEqual(BC.compare_forecasts(other, self.base), [])

    def test_exit_codes(self):
        self.assertEqual(BC.exit_code([("a", BC.PASS, ""), ("b", BC.SKIP, "")]), 0)
        self.assertEqual(BC.exit_code([("a", BC.WARN, "")]), 2)
        self.assertEqual(BC.exit_code([("a", BC.WARN, ""), ("b", BC.FAIL, "")]), 1)


class BrokenWindowsAreBrokenInTheRightWay(unittest.TestCase):
    @unittest.skipUnless(READY, "needs predict_lstm.py and docs/API_CONTRACT.md")
    def test_the_real_validator_gives_exactly_the_intended_code(self):
        import pandas as pd
        import api_client
        for code, window in BC.broken_windows().items():
            with self.subTest(code=code):
                df = pd.DataFrame(api_client.build_payload(window)["window"])
                try:
                    TA.VALIDATE(df)
                    got = None
                except TA.VALIDATION_ERROR as e:
                    got = e.code
                self.assertEqual(got, code)
        self.assertEqual(sorted(BC.broken_windows()), sorted(CODES))


@unittest.skipUnless(READY, "needs predict_lstm.py and docs/API_CONTRACT.md")
class RunChecksAgainstStandIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TA.QuietServer(("127.0.0.1", 0), TA.Stub)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()

    def setUp(self):
        TA.Stub.mode, TA.Stub.delay = "normal", 0.0

    def test_a_correct_backend_passes_everything(self):
        res = BC.run_checks(self.url, out=lambda *_: None)
        self.assertEqual(BC.exit_code(res), 0, res)
        r = by_name(res)
        self.assertEqual(r["GET /health"][0], BC.PASS)
        self.assertEqual(r["POST /predict with a valid window"][0], BC.PASS)
        for code in CODES:
            self.assertEqual(r[f"error code {code}"][0], BC.PASS, code)
        self.assertEqual(r["error code BAD_REQUEST (body without 'window')"][0], BC.PASS)
        self.assertEqual(r["backend equals model code for the same window"][0], BC.SKIP)

    def test_compare_passes_and_detects_a_difference(self):
        res = BC.run_checks(self.url, direct_fn=lambda w: copy.deepcopy(TA.SUCCESS_DOC), out=lambda *_: None)
        self.assertEqual(by_name(res)["backend equals model code for the same window"][0], BC.PASS)
        wrong = copy.deepcopy(TA.SUCCESS_DOC); wrong["predicted_bot_pct_next_minute"] = 40.0
        res = BC.run_checks(self.url, direct_fn=lambda w: wrong, out=lambda *_: None)
        status, detail = by_name(res)["backend equals model code for the same window"]
        self.assertEqual(status, BC.FAIL); self.assertIn("predicted_bot_pct_next_minute", detail)
        self.assertEqual(BC.exit_code(res), 1)

    def test_a_backend_in_mock_mode_is_not_a_pass(self):
        TA.Stub.mode = "mock"                   # always answers 200 with placeholders, so it also fails the error-code checks
        res = BC.run_checks(self.url, direct_fn=lambda w: {}, out=lambda *_: None)
        r = by_name(res)
        self.assertEqual(r["POST /predict with a valid window"][0], BC.WARN)
        self.assertEqual(r["backend equals model code for the same window"][0], BC.SKIP)
        self.assertEqual(r["error code NEGATIVE_VALUE"][0], BC.FAIL)
        self.assertEqual(BC.exit_code(res), 1)

    def test_server_errors_are_reported(self):
        TA.Stub.mode = "http500_json"
        res = BC.run_checks(self.url, out=lambda *_: None)
        self.assertEqual(by_name(res)["POST /predict with a valid window"][0], BC.FAIL)
        self.assertEqual(BC.exit_code(res), 1)

    def test_unreachable_backend_stops_early(self):
        res = BC.run_checks("http://127.0.0.1:9", out=lambda *_: None)
        self.assertEqual([(n, s) for n, s, _ in res], [("GET /health", BC.FAIL)])


if __name__ == "__main__":
    unittest.main()
