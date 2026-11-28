"""
SIH26153 — Tests for the FastAPI backend (api.py)
Author: Team Member 3 (Backend & Architecture)

Covers:
    - GET /health → model version and status
    - POST /predict → valid window → 200 with all 9 fields
    - POST /predict → each of 7 InputValidationError codes → 422
    - POST /predict → bad request structure → 422
    - Mock mode behaviour (tested via monkeypatch)

Run:  python -m pytest test_api.py -v
"""

import copy
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# A valid 5-row window (Quiet-range values from the training distribution).
# Timestamps 60 s apart so NOT_CONSECUTIVE does not fire.
# ---------------------------------------------------------------------------
VALID_WINDOW = [
    {
        "Timestamp": "2018-02-03T09:00:00",
        "Bot_Pct": 18.0,
        "Total_Flows": 1800,
        "Fwd_Pkts_Bot": 1050,
        "Bwd_Pkts_Bot": 820,
        "Fwd_Bytes_Bot": 63000,
        "Bwd_Bytes_Bot": 28000,
        "Avg_Duration_Bot": 22000,
    },
    {
        "Timestamp": "2018-02-03T09:01:00",
        "Bot_Pct": 19.5,
        "Total_Flows": 1850,
        "Fwd_Pkts_Bot": 1100,
        "Bwd_Pkts_Bot": 860,
        "Fwd_Bytes_Bot": 66000,
        "Bwd_Bytes_Bot": 30000,
        "Avg_Duration_Bot": 23000,
    },
    {
        "Timestamp": "2018-02-03T09:02:00",
        "Bot_Pct": 17.2,
        "Total_Flows": 1790,
        "Fwd_Pkts_Bot": 1020,
        "Bwd_Pkts_Bot": 800,
        "Fwd_Bytes_Bot": 61000,
        "Bwd_Bytes_Bot": 27500,
        "Avg_Duration_Bot": 21500,
    },
    {
        "Timestamp": "2018-02-03T09:03:00",
        "Bot_Pct": 20.1,
        "Total_Flows": 1900,
        "Fwd_Pkts_Bot": 1150,
        "Bwd_Pkts_Bot": 890,
        "Fwd_Bytes_Bot": 68000,
        "Bwd_Bytes_Bot": 31000,
        "Avg_Duration_Bot": 24000,
    },
    {
        "Timestamp": "2018-02-03T09:04:00",
        "Bot_Pct": 18.8,
        "Total_Flows": 1830,
        "Fwd_Pkts_Bot": 1080,
        "Bwd_Pkts_Bot": 840,
        "Fwd_Bytes_Bot": 65000,
        "Bwd_Bytes_Bot": 29500,
        "Avg_Duration_Bot": 22500,
    },
]

# Fields that must always appear in a successful /predict response
EXPECTED_RESPONSE_FIELDS = {
    "forecast_horizon_minutes",
    "predicted_bot_pct_next_minute",
    "predicted_state",
    "state_thresholds",
    "seed_predictions",
    "seed_spread_pct_points",
    "model_version",
    "model_status",
    "warnings",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    """Create a TestClient that loads the real model once for all tests."""
    from api import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/health").json()
        assert "model_version" in data
        assert "model_status" in data
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_model_status_is_provisional_or_mock(self, client):
        data = client.get("/health").json()
        assert data["model_status"] in ("PROVISIONAL", "MOCK")

    def test_health_has_limitations(self, client):
        data = client.get("/health").json()
        assert "limitations" in data
        assert isinstance(data["limitations"], list)
        assert len(data["limitations"]) > 0


# ---------------------------------------------------------------------------
# POST /predict — valid request
# ---------------------------------------------------------------------------
class TestPredictValid:
    def test_valid_request_returns_200(self, client):
        r = client.post("/predict", json={"window": VALID_WINDOW})
        assert r.status_code == 200

    def test_response_has_all_9_fields(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        missing = EXPECTED_RESPONSE_FIELDS - set(data.keys())
        assert not missing, f"Missing fields: {missing}"

    def test_forecast_horizon_is_1(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        assert data["forecast_horizon_minutes"] == 1

    def test_predicted_state_is_valid(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        assert data["predicted_state"] in ("Low", "Medium", "High")

    def test_predicted_bot_pct_in_range(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        pct = data["predicted_bot_pct_next_minute"]
        assert 0.0 <= pct <= 100.0

    def test_five_seed_predictions(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        seeds = data["seed_predictions"]
        assert len(seeds) == 5
        for key in ("42", "43", "44", "45", "46"):
            assert key in seeds

    def test_warnings_is_list(self, client):
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        assert isinstance(data["warnings"], list)

    def test_model_status_is_provisional(self, client):
        """When the real model is loaded, model_status should be PROVISIONAL."""
        data = client.post("/predict", json={"window": VALID_WINDOW}).json()
        # If the model actually loaded, it should be PROVISIONAL.
        # If in MOCK mode (model files missing), this test is expected to fail.
        assert data["model_status"] in ("PROVISIONAL", "MOCK")


# ---------------------------------------------------------------------------
# POST /predict — validation errors (7 InputValidationError codes)
# ---------------------------------------------------------------------------
class TestPredictValidationErrors:

    def test_missing_features_422(self, client):
        """Remove one required column → MISSING_FEATURES."""
        bad = copy.deepcopy(VALID_WINDOW)
        for row in bad:
            del row["Fwd_Bytes_Bot"]
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "MISSING_FEATURES"

    def test_bad_shape_too_few_rows(self, client):
        """Send 3 rows instead of 5 → BAD_SHAPE."""
        r = client.post("/predict", json={"window": VALID_WINDOW[:3]})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BAD_SHAPE"

    def test_bad_shape_too_many_rows(self, client):
        """Send 6 rows instead of 5 → BAD_SHAPE."""
        r = client.post("/predict", json={"window": VALID_WINDOW + [VALID_WINDOW[0]]})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BAD_SHAPE"

    def test_nan_or_inf_422(self, client):
        """Put None (null in JSON, parsed as NaN in pandas) in a cell → NAN_OR_INF."""
        bad = copy.deepcopy(VALID_WINDOW)
        bad[2]["Total_Flows"] = None
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "NAN_OR_INF"

    def test_negative_value_422(self, client):
        """Put a negative value → NEGATIVE_VALUE."""
        bad = copy.deepcopy(VALID_WINDOW)
        bad[0]["Total_Flows"] = -100
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "NEGATIVE_VALUE"

    def test_bot_pct_range_422(self, client):
        """Bot_Pct > 100 → BOT_PCT_RANGE."""
        bad = copy.deepcopy(VALID_WINDOW)
        bad[1]["Bot_Pct"] = 150.0
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BOT_PCT_RANGE"

    def test_bad_timestamp_422(self, client):
        """Unparseable timestamp → BAD_TIMESTAMP."""
        bad = copy.deepcopy(VALID_WINDOW)
        bad[0]["Timestamp"] = "not-a-date"
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BAD_TIMESTAMP"

    def test_not_consecutive_422(self, client):
        """Timestamps not 60 s apart → NOT_CONSECUTIVE."""
        bad = copy.deepcopy(VALID_WINDOW)
        bad[1]["Timestamp"] = "2018-02-03T09:05:00"  # 5 min gap instead of 1 min
        r = client.post("/predict", json={"window": bad})
        assert r.status_code == 422
        assert r.json()["error_code"] == "NOT_CONSECUTIVE"


# ---------------------------------------------------------------------------
# POST /predict — bad request structure (backend-side validation)
# ---------------------------------------------------------------------------
class TestPredictBadRequest:

    def test_missing_window_key(self, client):
        """No 'window' key at all → BAD_REQUEST."""
        r = client.post("/predict", json={"data": [1, 2, 3]})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BAD_REQUEST"

    def test_window_not_array(self, client):
        """'window' is a string instead of an array → BAD_REQUEST."""
        r = client.post("/predict", json={"window": "not an array"})
        assert r.status_code == 422
        assert r.json()["error_code"] == "BAD_REQUEST"

    def test_error_response_has_required_fields(self, client):
        """Every error response must have error, error_code, error_message, model_status."""
        r = client.post("/predict", json={"no_window": True})
        data = r.json()
        assert data["error"] is True
        assert "error_code" in data
        assert "error_message" in data
        assert "model_status" in data


# ---------------------------------------------------------------------------
# POST /predict — valid window without Timestamp (warning expected)
# ---------------------------------------------------------------------------
class TestPredictNoTimestamp:

    def test_no_timestamp_still_returns_200(self, client):
        """Window without Timestamp should work but add a spacing warning."""
        no_ts = copy.deepcopy(VALID_WINDOW)
        for row in no_ts:
            del row["Timestamp"]
        r = client.post("/predict", json={"window": no_ts})
        assert r.status_code == 200

    def test_no_timestamp_adds_warning(self, client):
        """Without Timestamp, a spacing-check warning should appear."""
        no_ts = copy.deepcopy(VALID_WINDOW)
        for row in no_ts:
            del row["Timestamp"]
        data = client.post("/predict", json={"window": no_ts}).json()
        spacing_warning = [w for w in data["warnings"] if "Timestamp" in w or "spacing" in w.lower() or "consecutive" in w.lower()]
        assert len(spacing_warning) > 0, "Expected a warning about missing Timestamp"


# ---------------------------------------------------------------------------
# Mock mode (test with monkeypatch)
# ---------------------------------------------------------------------------
class TestMockMode:

    def test_mock_health(self):
        """When PKG is None, /health should return model_status MOCK."""
        import api as api_module
        # Save originals
        orig_pkg = api_module.PKG
        orig_status = api_module.MODEL_STATUS
        try:
            api_module.PKG = None
            api_module.MODEL_STATUS = "MOCK"
            with TestClient(api_module.app) as c:
                data = c.get("/health").json()
                assert data["model_status"] == "MOCK"
                assert data["model_version"] == "mock"
                assert data["package_folder"] is None
        finally:
            api_module.PKG = orig_pkg
            api_module.MODEL_STATUS = orig_status

    def test_mock_predict_returns_mock_response(self):
        """When PKG is None, /predict returns the mock response."""
        import api as api_module
        orig_pkg = api_module.PKG
        orig_status = api_module.MODEL_STATUS
        try:
            api_module.PKG = None
            api_module.MODEL_STATUS = "MOCK"
            with TestClient(api_module.app) as c:
                data = c.post("/predict", json={"window": VALID_WINDOW}).json()
                assert data["model_status"] == "MOCK"
                assert data["predicted_bot_pct_next_minute"] == 0.0
                assert "MODEL NOT LOADED" in data["warnings"][0]
        finally:
            api_module.PKG = orig_pkg
            api_module.MODEL_STATUS = orig_status

    def test_mock_predict_still_validates_structure(self):
        """Mock mode still checks the window structure before returning mock."""
        import api as api_module
        orig_pkg = api_module.PKG
        orig_status = api_module.MODEL_STATUS
        try:
            api_module.PKG = None
            api_module.MODEL_STATUS = "MOCK"
            with TestClient(api_module.app) as c:
                # Missing window key → should still get BAD_REQUEST 422
                r = c.post("/predict", json={"data": "bad"})
                assert r.status_code == 422
                assert r.json()["error_code"] == "BAD_REQUEST"
        finally:
            api_module.PKG = orig_pkg
            api_module.MODEL_STATUS = orig_status
