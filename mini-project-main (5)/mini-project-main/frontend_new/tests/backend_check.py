"""Integration check for a RUNNING backend (Members 3 and 4). It tests the real API against docs/API_CONTRACT.md.

    python tests/backend_check.py --url http://localhost:8000
    python tests/backend_check.py --url http://localhost:8000 --compare PATH_TO_UNZIPPED_MODEL_FOLDER

Without --compare it checks the connection, one forecast, and every error code. With --compare it also loads the model directly
(needs TensorFlow and ../predict_lstm.py) and checks that the backend returns exactly what the model code returns for the same
window, so a real forecast is shown to travel unchanged from the model through the backend. Exit code: 0 all good, 1 something
failed, 2 no failures but the backend is in MOCK mode (placeholder values, so this is NOT a real-model integration pass).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

FRONT = Path(__file__).resolve().parents[1]
ROOT = FRONT.parent
sys.path.insert(0, str(FRONT))
import api_client as api
import validation as V

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"


def good_window():
    return V.table_to_window(V.presets()["Typical traffic (example)"], V.DEFAULT_START)[0]


def broken_windows():
    """One window per backend error code, each broken in exactly one way."""
    w = good_window()

    def edit(fn):
        d = w.copy()
        fn(d)
        return d

    def bad_ts(d):
        d["Timestamp"] = d["Timestamp"].astype(object)
        d.loc[1, "Timestamp"] = "not a date"

    return {
        "MISSING_FEATURES": w.drop(columns=["Fwd_Bytes_Bot"]),
        "BAD_TIMESTAMP": edit(bad_ts),
        "NOT_CONSECUTIVE": edit(lambda d: d.__setitem__("Timestamp", d["Timestamp"] + pd.to_timedelta([0, 0, 0, 5, 5], unit="min"))),
        "BAD_SHAPE": w.iloc[:4],
        "NAN_OR_INF": edit(lambda d: d.loc.__setitem__((2, "Total_Flows"), np.nan)),
        "NEGATIVE_VALUE": edit(lambda d: d.loc.__setitem__((0, "Total_Flows"), -1.0)),
        "BOT_PCT_RANGE": edit(lambda d: d.loc.__setitem__((4, "Bot_Pct"), 101.0)),
    }


def compare_forecasts(got, want, tol=1e-3):
    """List of differences between the backend's forecast and the model code's forecast for the same window."""
    problems = []
    for k in ("forecast_horizon_minutes", "predicted_state", "state_thresholds", "model_version", "model_status"):
        if got.get(k) != want.get(k):
            problems.append(f"{k}: backend {got.get(k)!r}, model code {want.get(k)!r}")
    for k in ("predicted_bot_pct_next_minute", "seed_spread_pct_points"):
        if abs(float(got[k]) - float(want[k])) > tol:
            problems.append(f"{k}: backend {got[k]}, model code {want[k]}")
    if set(got["seed_predictions"]) != set(want["seed_predictions"]):
        problems.append(f"seed_predictions keys differ: {sorted(got['seed_predictions'])} vs {sorted(want['seed_predictions'])}")
    else:
        for s, v in want["seed_predictions"].items():
            if abs(float(got["seed_predictions"][s]) - float(v)) > tol:
                problems.append(f"seed {s}: backend {got['seed_predictions'][s]}, model code {v}")
    missing = [w for w in want["warnings"] if w not in got["warnings"]]
    if missing:
        problems.append(f"warnings missing from the backend response: {missing}")
    return problems


def run_checks(base_url, direct_fn=None, out=print):
    """Run every check and return a list of (name, status, detail). direct_fn(window DataFrame) -> forecast dict, optional."""
    results = []

    def add(name, status, detail=""):
        results.append((name, status, detail))
        out(f"{status:<5} {name}" + (f": {detail}" if detail else ""))

    try:
        h = api.fetch_health(base_url)
    except api.ApiError as e:
        add("GET /health", FAIL, str(e))
        if e.code in ("BACKEND_UNREACHABLE", "BACKEND_TIMEOUT", "BAD_URL"):
            return results                                         # nothing else can work
    else:
        add("GET /health", WARN if api.is_mock(h) else PASS, f"model_status={h['model_status']}, model_version={h['model_version']}")

    window = good_window()
    forecast = None
    try:
        forecast = api.request_forecast(window, base_url)
    except api.ApiError as e:
        add("POST /predict with a valid window", FAIL, str(e))
    else:
        add("POST /predict with a valid window", WARN if api.is_mock(forecast) else PASS,
            f"{forecast['predicted_bot_pct_next_minute']}% {forecast['predicted_state']}, "
            f"disagreement {forecast['seed_spread_pct_points']}, model_status={forecast['model_status']}")

    for code, bad in broken_windows().items():
        name = f"error code {code}"
        try:
            api.request_forecast(bad, base_url)
        except api.ApiError as e:
            ok = e.code == code and e.http_status == 422
            add(name, PASS if ok else FAIL, "" if ok else f"expected {code} with HTTP 422, got {e.code} with HTTP {e.http_status}")
        else:
            add(name, FAIL, "the backend accepted a window that should be rejected")

    try:
        r = requests.post(api.normalise_base_url(base_url) + "/predict", json={"nope": 1}, timeout=api.PREDICT_TIMEOUT_S)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        ok = r.status_code == 422 and body.get("error_code") == "BAD_REQUEST"
        add("error code BAD_REQUEST (body without 'window')", PASS if ok else FAIL,
            "" if ok else f"expected HTTP 422 BAD_REQUEST, got HTTP {r.status_code} {body.get('error_code')}")
    except (requests.RequestException, ValueError) as e:
        add("error code BAD_REQUEST (body without 'window')", FAIL, f"{type(e).__name__}")

    if direct_fn is None:
        add("backend equals model code for the same window", SKIP, "run with --compare PATH_TO_MODEL_FOLDER to enable")
    elif forecast is None or api.is_mock(forecast):
        add("backend equals model code for the same window", SKIP, "no real forecast to compare (backend failed or is in MOCK mode)")
    else:
        problems = compare_forecasts(forecast, direct_fn(window))
        add("backend equals model code for the same window", FAIL if problems else PASS, "; ".join(problems))
    return results


def exit_code(results):
    if any(s == FAIL for _, s, _ in results):
        return 1
    return 2 if any(s == WARN for _, s, _ in results) else 0


def load_direct(model_folder):
    sys.path.insert(0, str(ROOT))
    import predict_lstm                                            # needs TensorFlow; imported only when --compare is used
    pkg = predict_lstm.load_package(model_folder)
    return lambda window: predict_lstm.predict_next_minute(pkg, window)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=api.DEFAULT_BASE_URL)
    ap.add_argument("--compare", metavar="MODEL_FOLDER", help="unzipped phase4_lstm_REGEN_v1_... folder")
    args = ap.parse_args()
    print(f"Checking the backend at {args.url}\n")
    results = run_checks(args.url, load_direct(args.compare) if args.compare else None)
    code = exit_code(results)
    print("\n" + {0: "ALL CHECKS PASSED", 1: "SOME CHECKS FAILED",
                  2: "No failures, but the backend is in MOCK mode: these are placeholder values, not a real-model integration pass."}[code])
    sys.exit(code)


if __name__ == "__main__":
    main()
