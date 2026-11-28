"""Tests for api_client.py and ui_text.py.  Run from the frontend/ folder:   python -m unittest discover -s tests -v

A small stand-in backend is started on a free local port. For POST /predict it uses the REAL validate_window() from
../predict_lstm.py and the example request/response written in ../docs/API_CONTRACT.md, so the client is checked
against the repo's own validator and contract. Tests that need those files are skipped when they are not found.
"""
import json, re, sys, threading, time, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONT = Path(__file__).resolve().parents[1]
ROOT = FRONT.parent
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(ROOT))
import api_client as api
import ui_text as T

try:
    import pandas as pd
    import predict_lstm
    VALIDATE, VALIDATION_ERROR = predict_lstm.validate_window, predict_lstm.InputValidationError
except Exception:                                    # pandas/numpy/joblib missing, or predict_lstm.py not in the repo root
    pd = VALIDATE = VALIDATION_ERROR = None

DOC_PATH = ROOT / "docs" / "API_CONTRACT.md"
DOC = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else None


def block_after(heading):
    i = DOC.index(heading)
    return json.loads(re.search(r"```json\s*(.*?)```", DOC[i:], re.S).group(1))


if DOC:
    EXAMPLE_REQUEST = block_after("### Complete example request")
    SUCCESS_DOC = block_after("## 4. Success Response Schema")
    HEALTH_DOC = block_after("#### Health response schema")
    MOCK_FORECAST_DOC = block_after("### Mock response")
    MOCK_HEALTH_DOC = block_after("If the model failed to load")


class Stub(BaseHTTPRequestHandler):
    mode, delay = "normal", 0.0

    def log_message(self, *a):
        pass

    def send_json(self, status, body, raw=None):
        data = raw if raw is not None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def err(self, status, code, msg):
        self.send_json(status, {"error": True, "error_code": code, "error_message": msg, "model_status": "PROVISIONAL"})

    def do_GET(self):
        if Stub.mode == "http500_text":
            return self.send_json(500, None, raw=b"Internal Server Error")
        if Stub.mode == "health_bad":
            return self.send_json(200, {"status": "ok"})
        self.send_json(200, HEALTH_DOC)

    def do_POST(self):
        time.sleep(Stub.delay)
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        m = Stub.mode
        if m == "http500_text":
            return self.send_json(500, None, raw=b"Internal Server Error")
        if m == "http500_json":
            return self.err(500, "SERVER_ERROR", "boom")
        if m == "not_json":
            return self.send_json(200, None, raw=b"<html>not json</html>")
        if m == "missing_keys":
            return self.send_json(200, {"predicted_state": "Low"})
        if m == "bad_status":
            return self.send_json(200, dict(SUCCESS_DOC, model_status="LIVE"))
        if m == "mock":
            return self.send_json(200, MOCK_FORECAST_DOC)
        body = json.loads(raw)
        if not isinstance(body, dict) or "window" not in body or not isinstance(body["window"], list):
            return self.err(422, "BAD_REQUEST", "request body must be an object with a 'window' list")
        if len(body["window"]) != 5:
            return self.err(422, "BAD_SHAPE", "window must have exactly 5 rows")
        try:
            VALIDATE(pd.DataFrame(body["window"]))
        except VALIDATION_ERROR as e:
            return self.err(422, e.code, str(e))
        self.send_json(200, SUCCESS_DOC)


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, *a):
        pass


class WithServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = QuietServer(("127.0.0.1", 0), Stub)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Stub.mode, Stub.delay = "normal", 0.0

    def window(self):
        return json.loads(json.dumps(EXAMPLE_REQUEST["window"]))

    def code_of(self, window):
        with self.assertRaises(api.ApiError) as cm:
            api.request_forecast(window, self.url)
        return cm.exception


@unittest.skipUnless(DOC and VALIDATE, "needs docs/API_CONTRACT.md and predict_lstm.py (with pandas/numpy/joblib)")
class AgainstContractAndRealValidator(WithServer):
    def test_example_request_succeeds_and_is_returned_unchanged(self):
        self.assertEqual(api.request_forecast(self.window(), self.url), SUCCESS_DOC)

    def test_health_matches_contract(self):
        self.assertEqual(api.fetch_health(self.url), HEALTH_DOC)

    def test_dataframe_with_timestamps_and_numpy_types(self):
        df = pd.DataFrame(self.window())
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        payload = api.build_payload(df)
        json.dumps(payload)                                              # must be JSON-serialisable
        self.assertEqual(payload["window"][0]["Timestamp"], "2018-02-03T09:00:00")
        self.assertEqual(payload, api.build_payload(self.window()))
        self.assertEqual(api.request_forecast(df, self.url), SUCCESS_DOC)

    def test_every_validator_error_code_reaches_the_client(self):
        def edit(fn):
            w = self.window(); fn(w); return w
        cases = {
            "MISSING_FEATURES": edit(lambda w: [r.pop("Fwd_Bytes_Bot") for r in w]),   # missing from every row
            "BAD_TIMESTAMP": edit(lambda w: w[1].update(Timestamp="not a date")),
            "NOT_CONSECUTIVE": edit(lambda w: w[3].update(Timestamp="2018-02-03T09:05:00")),
            "NEGATIVE_VALUE": edit(lambda w: w[0].update(Total_Flows=-1)),
            "BOT_PCT_RANGE": edit(lambda w: w[4].update(Bot_Pct=101.0)),
            "NAN_OR_INF": edit(lambda w: w[2].update(Total_Flows=float("nan"))),
            "BAD_SHAPE": self.window()[:4],
        }
        for code, window in cases.items():
            with self.subTest(code=code):
                e = self.code_of(window)
                self.assertEqual((e.code, e.http_status, e.model_status), (code, 422, "PROVISIONAL"))
                self.assertIn(code, T.ERROR_MESSAGES)
                self.assertIn(T.ERROR_MESSAGES[code], T.describe_error(e))

    def test_input_is_not_modified(self):
        w = self.window()
        w[1]["Timestamp"] = "2018-02-03T09:09:00"
        before = json.dumps(w)
        self.code_of(w)
        self.assertEqual(json.dumps(w), before)

    def test_mock_response_is_recognised(self):
        Stub.mode = "mock"
        out = api.request_forecast(self.window(), self.url)
        self.assertTrue(api.is_mock(out))
        self.assertEqual(out, MOCK_FORECAST_DOC)


@unittest.skipUnless(DOC, "needs docs/API_CONTRACT.md")
class BadBackendBehaviour(WithServer):
    def test_http500_without_json(self):
        Stub.mode = "http500_text"
        with self.assertRaises(api.ApiError) as cm:
            api.request_forecast(EXAMPLE_REQUEST["window"], self.url)
        self.assertEqual((cm.exception.code, cm.exception.http_status), ("SERVER_ERROR", 500))
        with self.assertRaises(api.ApiError) as cm:
            api.fetch_health(self.url)
        self.assertEqual(cm.exception.code, "SERVER_ERROR")

    def test_http500_with_contract_error_body(self):
        Stub.mode = "http500_json"
        with self.assertRaises(api.ApiError) as cm:
            api.request_forecast(EXAMPLE_REQUEST["window"], self.url)
        self.assertEqual((cm.exception.code, cm.exception.http_status), ("SERVER_ERROR", 500))

    def test_bad_200_responses_are_rejected(self):
        for mode in ("not_json", "missing_keys", "bad_status"):
            with self.subTest(mode=mode):
                Stub.mode = mode
                with self.assertRaises(api.ApiError) as cm:
                    api.request_forecast(EXAMPLE_REQUEST["window"], self.url)
                self.assertEqual(cm.exception.code, "BAD_RESPONSE")
        Stub.mode = "health_bad"
        with self.assertRaises(api.ApiError) as cm:
            api.fetch_health(self.url)
        self.assertEqual(cm.exception.code, "BAD_RESPONSE")

    def test_timeout(self):
        Stub.delay = 1.5
        old = api.PREDICT_TIMEOUT_S
        api.PREDICT_TIMEOUT_S = 0.3
        try:
            with self.assertRaises(api.ApiError) as cm:
                api.request_forecast(EXAMPLE_REQUEST["window"], self.url)
        finally:
            api.PREDICT_TIMEOUT_S = old
        self.assertEqual(cm.exception.code, "BACKEND_TIMEOUT")


class NoServerNeeded(unittest.TestCase):
    def test_unreachable_backend(self):
        for call in (lambda: api.fetch_health("http://127.0.0.1:9"), lambda: api.request_forecast([{}] * 5, "http://127.0.0.1:9")):
            with self.assertRaises(api.ApiError) as cm:
                call()
            self.assertEqual(cm.exception.code, "BACKEND_UNREACHABLE")

    def test_bad_urls(self):
        for url in ("", "localhost:8000", "ftp://x", "http://", "http://host:notaport", None):
            with self.subTest(url=url):
                with self.assertRaises(api.ApiError) as cm:
                    api.fetch_health(url)
                self.assertEqual(cm.exception.code, "BAD_URL")
        self.assertEqual(api.normalise_base_url(" http://localhost:8000/ "), "http://localhost:8000")

    def test_demo_mode_uses_no_network_and_returns_labelled_mock(self):
        for url in ("http://127.0.0.1:9", "not a url"):
            f = api.request_forecast([{"Bot_Pct": 1.0}] * 5, url, demo=True)
            h = api.fetch_health(url, demo=True)
            self.assertTrue(api.is_mock(f) and api.is_mock(h))
            self.assertEqual(f["predicted_bot_pct_next_minute"], 0.0)
        f["warnings"].append("changed")                                  # returned copies must not alter the constants
        self.assertEqual(len(api.MOCK_FORECAST_RESPONSE["warnings"]), 2)

    def test_unreadable_window(self):
        with self.assertRaises(api.ApiError) as cm:
            api.request_forecast([1, 2, 3, 4, 5], "http://localhost:8000", demo=True)
        self.assertEqual(cm.exception.code, "BAD_INPUT")

    @unittest.skipUnless(DOC, "needs docs/API_CONTRACT.md")
    def test_demo_constants_match_contract_exactly(self):
        self.assertEqual(api.MOCK_FORECAST_RESPONSE, MOCK_FORECAST_DOC)
        self.assertEqual(api.MOCK_HEALTH_RESPONSE, MOCK_HEALTH_DOC)

    def test_every_client_error_code_has_a_message(self):
        used = set(re.findall(r'ApiError\(\s*"([A-Z_]+)"', (FRONT / "api_client.py").read_text(encoding="utf-8")))
        used |= {"MISSING_FEATURES", "BAD_SHAPE", "NAN_OR_INF", "NEGATIVE_VALUE", "BOT_PCT_RANGE", "BAD_TIMESTAMP",
                 "NOT_CONSECUTIVE", "BAD_REQUEST", "SERVER_ERROR"}
        self.assertEqual([c for c in sorted(used) if c not in T.ERROR_MESSAGES], [])

    def test_unknown_error_code_still_gives_a_message(self):
        self.assertIn("HTTP 418", T.describe_error(api.ApiError("HTTP_418", "teapot", 418)))

    def test_forbidden_wording_is_absent(self):
        banned = ("confidence", "accuracy", "certainty", "shap")
        for name in ("ui_text.py", "app.py", "api_client.py"):
            text = (FRONT / name).read_text(encoding="utf-8").lower()
            for word in banned:
                self.assertIsNone(re.search(rf"\b{word}\b", text), f"{word!r} found in {name}")

    def test_wording_states_the_limits(self):
        self.assertIn("not a real-time detector", T.PROVISIONAL_BANNER)
        self.assertIn("not be taken as proof", T.LOW_RECALL_NOTE)
        self.assertEqual(len(T.LIMITATIONS), 4)


if __name__ == "__main__":
    unittest.main()
