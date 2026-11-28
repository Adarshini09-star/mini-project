"""
SIH26153 — FastAPI Backend for AI-Based Network Attack Forecasting
Author: Team Member 3 (Backend & Architecture)

Endpoints:
    GET  /health   → model load status and version
    POST /predict  → accepts a 5-row window, returns next-minute bot-traffic forecast

Conforms to: docs/API_CONTRACT.md
"""

import os
import logging
import traceback

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import predict_lstm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_FOLDER = os.environ.get(
    "MODEL_FOLDER", "phase4_lstm_REGEN_v1_20261101_0503"
)

# ---------------------------------------------------------------------------
# Model loading — exactly once at startup
# ---------------------------------------------------------------------------
logger = logging.getLogger("sih26153.api")

try:
    PKG = predict_lstm.load_package(MODEL_FOLDER)
    MODEL_STATUS = "PROVISIONAL"
    logger.info("Model loaded successfully from %s", MODEL_FOLDER)
except Exception as exc:
    PKG = None
    MODEL_STATUS = "MOCK"
    logger.error("Model load FAILED — running in mock mode. Error: %s", exc)
    traceback.print_exc()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SIH26153 Network Attack Forecasting API",
    version="0.1.0",
    description="Offline/batch LSTM-based bot-traffic forecasting. PROVISIONAL model.",
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mock response (returned when PKG is None)
# ---------------------------------------------------------------------------
MOCK_PREDICT_RESPONSE = {
    "forecast_horizon_minutes": 1,
    "predicted_bot_pct_next_minute": 0.0,
    "predicted_state": "Low",
    "state_thresholds": {"Low": "<25", "Medium": "25-<50", "High": ">=50"},
    "seed_predictions": {"42": 0.0, "43": 0.0, "44": 0.0, "45": 0.0, "46": 0.0},
    "seed_spread_pct_points": 0.0,
    "model_version": "mock",
    "model_status": "MOCK",
    "warnings": [
        "MODEL NOT LOADED — this is a mock response. All values are placeholder zeros.",
        "Do not interpret these numbers as forecasts.",
    ],
}


def _error_response(code: str, message: str, status: int) -> JSONResponse:
    """Build a standard error JSON response per API_CONTRACT.md §5."""
    return JSONResponse(
        status_code=status,
        content={
            "error": True,
            "error_code": code,
            "error_message": message,
            "model_status": MODEL_STATUS,
        },
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    if PKG is not None:
        return {
            "status": "ok",
            "model_version": PKG["cfg"]["artifact_version"],
            "model_status": MODEL_STATUS,
            "package_folder": MODEL_FOLDER,
            "limitations": [
                "Offline/batch only. Not a live or real-time system.",
                "Low-state recall ~0% on the test day.",
                "Provisional model; not production-validated.",
            ],
        }
    else:
        return {
            "status": "ok",
            "model_version": "mock",
            "model_status": "MOCK",
            "package_folder": None,
            "limitations": [
                "Model could not be loaded. All predictions are mock values."
            ],
        }


# ---------------------------------------------------------------------------
# POST /predict
# ---------------------------------------------------------------------------
@app.post("/predict")
async def predict(request: Request):
    # --- Parse JSON body ---
    try:
        body = await request.json()
    except Exception:
        return _error_response(
            "BAD_REQUEST", "Request body is not valid JSON.", 422
        )

    # --- Validate top-level structure ---
    if not isinstance(body, dict) or "window" not in body:
        return _error_response(
            "BAD_REQUEST", "'window' key is missing from the request body.", 422
        )

    window = body["window"]
    if not isinstance(window, list):
        return _error_response(
            "BAD_REQUEST", "'window' must be a JSON array.", 422
        )

    if len(window) != 5:
        return _error_response(
            "BAD_SHAPE",
            f"'window' must contain exactly 5 row objects; got {len(window)}.",
            422,
        )

    # --- Mock mode: return fixed mock response ---
    if PKG is None:
        return MOCK_PREDICT_RESPONSE

    # --- Build a DataFrame from the window rows ---
    try:
        df = pd.DataFrame(window)
    except Exception as exc:
        return _error_response(
            "BAD_REQUEST",
            f"Could not convert window rows to a DataFrame: {exc}",
            422,
        )

    # --- Call predict_next_minute (which internally calls validate_window) ---
    try:
        result = predict_lstm.predict_next_minute(PKG, df)
        return result

    except predict_lstm.InputValidationError as exc:
        return _error_response(exc.code, str(exc), 422)

    except Exception as exc:
        logger.error("Unexpected error in /predict: %s", exc, exc_info=True)
        return _error_response("SERVER_ERROR", str(exc), 500)


# ---------------------------------------------------------------------------
# Run with: uvicorn api:app --host 0.0.0.0 --port 8000
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
