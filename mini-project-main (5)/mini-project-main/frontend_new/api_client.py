"""HTTP client for the SIH26153 backend (see docs/API_CONTRACT.md).

Rules this file follows:
  * It never loads the model, the scalers or predict_lstm.py. Every forecast comes from the backend over HTTP.
  * It never changes the data it is given and never invents a forecast.
  * Demo mode returns the placeholder response that API_CONTRACT.md defines for MOCK mode (model_status "MOCK").
    It contacts no backend, and the UI must label it clearly.
"""
import copy
import math
from urllib.parse import urlparse

import requests

FEATURES = ["Bot_Pct", "Total_Flows", "Fwd_Pkts_Bot", "Bwd_Pkts_Bot", "Fwd_Bytes_Bot", "Bwd_Bytes_Bot", "Avg_Duration_Bot"]
DEFAULT_BASE_URL = "http://localhost:8000"
HEALTH_TIMEOUT_S = 5
PREDICT_TIMEOUT_S = 30
STATES = ("Low", "Medium", "High")
MODEL_STATUSES = ("PROVISIONAL", "MOCK")

_FORECAST_KEYS = ("forecast_horizon_minutes", "predicted_bot_pct_next_minute", "predicted_state", "state_thresholds",
                  "seed_predictions", "seed_spread_pct_points", "model_version", "model_status", "warnings")
_HEALTH_KEYS = ("status", "model_version", "model_status", "limitations")

# Exactly the MOCK responses written in docs/API_CONTRACT.md (sections 2.2 and 8). Placeholder values, not forecasts.
MOCK_FORECAST_RESPONSE = {
    "forecast_horizon_minutes": 1,
    "predicted_bot_pct_next_minute": 0.0,
    "predicted_state": "Low",
    "state_thresholds": {"Low": "<25", "Medium": "25-<50", "High": ">=50"},
    "seed_predictions": {"42": 0.0, "43": 0.0, "44": 0.0, "45": 0.0, "46": 0.0},
    "seed_spread_pct_points": 0.0,
    "model_version": "mock",
    "model_status": "MOCK",
    "warnings": ["MODEL NOT LOADED — this is a mock response. All values are placeholder zeros.",
                 "Do not interpret these numbers as forecasts."],
}
MOCK_HEALTH_RESPONSE = {
    "status": "ok",
    "model_version": "mock",
    "model_status": "MOCK",
    "package_folder": None,
    "limitations": ["Model could not be loaded. All predictions are mock values."],
}


class ApiError(Exception):
    """Any failure talking to the backend. `code` is the backend's error_code, or one of the client codes:
    BAD_URL, BAD_INPUT, BACKEND_UNREACHABLE, BACKEND_TIMEOUT, REQUEST_FAILED, BAD_RESPONSE, SERVER_ERROR, HTTP_<n>."""

    def __init__(self, code, message, http_status=None, model_status=None):
        super().__init__(f"[{code}] {message}")
        self.code, self.message = code, message
        self.http_status, self.model_status = http_status, model_status


def is_mock(payload):
    """True when a response says it came from MOCK mode."""
    return isinstance(payload, dict) and payload.get("model_status") == "MOCK"


def normalise_base_url(base_url):
    url = (base_url or "").strip().rstrip("/")
    try:
        p = urlparse(url)
        _ = p.port
        ok = p.scheme in ("http", "https") and bool(p.netloc) and bool(p.hostname)
    except ValueError:
        ok = False
    if not ok:
        raise ApiError("BAD_URL", f"'{base_url}' is not a valid address. Example: {DEFAULT_BASE_URL}")
    return url


def _clean(value):
    if hasattr(value, "isoformat"):                       # datetime / pandas Timestamp -> ISO 8601 text
        return value.isoformat()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):   # numpy scalar -> Python number
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None                                       # JSON has no NaN/inf; the backend reports NAN_OR_INF
    return value


def build_payload(window):
    """{"window": [row, ...]} from a list of dicts or a pandas DataFrame. Rows keep their order and values;
    only the data types are made JSON-safe. Nothing is dropped, filled or corrected."""
    try:
        rows = window.to_dict("records") if hasattr(window, "to_dict") else list(window)
        return {"window": [{str(k): _clean(v) for k, v in dict(r).items()} for r in rows]}
    except (TypeError, ValueError) as e:
        raise ApiError("BAD_INPUT", f"the window could not be converted to rows of named values ({e})")


def _json_or_none(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _error_from(resp):
    body = _json_or_none(resp)
    if isinstance(body, dict) and body.get("error") is True and isinstance(body.get("error_code"), str):
        return ApiError(body["error_code"], str(body.get("error_message", "")), resp.status_code, body.get("model_status"))
    code = "SERVER_ERROR" if resp.status_code >= 500 else f"HTTP_{resp.status_code}"
    return ApiError(code, f"the backend answered HTTP {resp.status_code} without a readable error body", resp.status_code)


def _send(method, url, timeout, **kwargs):
    try:
        return requests.request(method, url, timeout=timeout, **kwargs)
    except requests.exceptions.Timeout:
        raise ApiError("BACKEND_TIMEOUT", f"no answer from {url} within {timeout} seconds")
    except requests.exceptions.ConnectionError:
        raise ApiError("BACKEND_UNREACHABLE", f"could not connect to {url}")
    except requests.exceptions.RequestException as e:
        raise ApiError("REQUEST_FAILED", f"the request failed ({type(e).__name__})")


def _bad(message):
    return ApiError("BAD_RESPONSE", message, http_status=200)


def _check_health(body):
    if not isinstance(body, dict) or [k for k in _HEALTH_KEYS if k not in body]:
        raise _bad("the health response is missing required fields")
    if body["model_status"] not in MODEL_STATUSES or not isinstance(body["limitations"], list):
        raise _bad("the health response has an unexpected model_status or limitations")
    return body


def _check_forecast(body):
    if not isinstance(body, dict):
        raise _bad("the forecast response is not a JSON object")
    missing = [k for k in _FORECAST_KEYS if k not in body]
    if missing:
        raise _bad(f"the forecast response is missing fields: {missing}")
    pct, spread = body["predicted_bot_pct_next_minute"], body["seed_spread_pct_points"]
    if not (_is_number(pct) and 0 <= pct <= 100) or not (_is_number(spread) and spread >= 0):
        raise _bad("the forecast percentage or model disagreement is not a valid number")
    if body["predicted_state"] not in STATES or body["model_status"] not in MODEL_STATUSES:
        raise _bad("the forecast has an unexpected predicted_state or model_status")
    if not isinstance(body["seed_predictions"], dict) or not isinstance(body["warnings"], list) \
            or not all(isinstance(w, str) for w in body["warnings"]):
        raise _bad("the forecast seed_predictions or warnings have the wrong type")
    return body


def fetch_health(base_url, demo=False):
    """GET /health. Returns the health dict. In demo mode returns the contract's MOCK health with no network call."""
    if demo:
        return copy.deepcopy(MOCK_HEALTH_RESPONSE)
    resp = _send("GET", normalise_base_url(base_url) + "/health", HEALTH_TIMEOUT_S)
    if resp.status_code != 200:
        raise _error_from(resp)
    return _check_health(_json_or_none(resp))


def request_forecast(window, base_url, demo=False):
    """POST /predict with {"window": [...5 rows...]}. Returns the forecast dict exactly as the backend sent it.
    In demo mode returns the contract's MOCK forecast with no network call (the UI must label it as a placeholder)."""
    payload = build_payload(window)
    if demo:
        return copy.deepcopy(MOCK_FORECAST_RESPONSE)
    resp = _send("POST", normalise_base_url(base_url) + "/predict", PREDICT_TIMEOUT_S, json=payload)
    if resp.status_code != 200:
        raise _error_from(resp)
    return _check_forecast(_json_or_none(resp))
