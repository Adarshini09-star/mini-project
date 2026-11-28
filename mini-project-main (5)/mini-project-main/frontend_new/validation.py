"""Input checks and CSV reading for the dashboard (Phase 2).

validate_window() repeats the checks of predict_lstm.validate_window() in the same order and with the same error codes,
so a problem is shown to the user BEFORE a request is sent. The backend still validates everything again: these checks
only give faster, clearer feedback. This file contains no model logic. It never changes the values it checks.
"""
import io
import warnings
from collections import namedtuple

import numpy as np
import pandas as pd

from api_client import FEATURES

WINDOW_ROWS = 5
MAX_CSV_BYTES = 10_000_000
DEFAULT_START = "2018-02-03 09:00:00"

Issue = namedtuple("Issue", "code detail")


class InputFileError(Exception):
    """The uploaded file could not be turned into a table. `code` is a key of ui_text.ERROR_MESSAGES."""

    def __init__(self, code, detail):
        super().__init__(f"[{code}] {detail}")
        self.code, self.detail = code, detail


def _to_datetime(values):
    with warnings.catch_warnings():                      # mixed text formats only trigger a pandas format warning
        warnings.simplefilter("ignore")
        return pd.to_datetime(values, errors="coerce")


def _rows(mask_rows):
    return ", ".join(str(int(i) + 1) for i in mask_rows[:5]) + (" ..." if len(mask_rows) > 5 else "")


def validate_window(df):
    """List of Issue(code, detail) found in a table, in the backend's order. An empty list means it looks valid.
    The table needs the 7 feature columns and may have a Timestamp column."""
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        return [Issue("MISSING_FEATURES", f"missing columns: {missing}")]
    issues = []
    if "Timestamp" in df.columns:
        ts = _to_datetime(df["Timestamp"])
        bad = np.flatnonzero(ts.isna().to_numpy())
        if len(bad):
            issues.append(Issue("BAD_TIMESTAMP", f"cannot read the Timestamp in row(s) {_rows(bad)}"))
        else:
            gaps = ts.diff().dropna().dt.total_seconds().to_numpy()
            if not np.all(gaps == 60):
                issues.append(Issue("NOT_CONSECUTIVE", f"gaps between rows (seconds): {sorted(set(gaps.tolist()))}"))
    if len(df) != WINDOW_ROWS:
        issues.append(Issue("BAD_SHAPE", f"expected {WINDOW_ROWS} rows, got {len(df)}"))
    raw = df[FEATURES]
    num = raw.apply(pd.to_numeric, errors="coerce")
    text_cells = (raw.notna() & num.isna()).to_numpy()
    if text_cells.any():
        r, c = np.argwhere(text_cells)[0]
        issues.append(Issue("NOT_NUMERIC", f"row {r + 1}, column {FEATURES[c]} is not a number"))
    arr = num.to_numpy(dtype=float)
    nonfinite = ~np.isfinite(arr) & ~text_cells
    if nonfinite.any():
        r, c = np.argwhere(nonfinite)[0]
        issues.append(Issue("NAN_OR_INF", f"row {r + 1}, column {FEATURES[c]} is empty or infinite"))
    if (arr < 0).any():
        r, c = np.argwhere(arr < 0)[0]
        issues.append(Issue("NEGATIVE_VALUE", f"row {r + 1}, column {FEATURES[c]} is negative"))
    if (arr[:, 0] > 100).any():
        issues.append(Issue("BOT_PCT_RANGE", f"Bot_Pct above 100 in row(s) {_rows(np.flatnonzero(arr[:, 0] > 100))}"))
    return issues


def table_to_window(table, start_text):
    """Typed table (7 feature columns, one row per minute, oldest first) -> (window DataFrame or None, issues).
    The rows are labelled with consecutive minutes counted from `start_text`; the labels only mark the order."""
    start = _to_datetime(start_text)
    if pd.isna(start):
        return None, [Issue("BAD_TIMESTAMP", f"cannot read the start time '{start_text}'. Use YYYY-MM-DD HH:MM:SS")]
    window = table[[c for c in FEATURES if c in table.columns]].reset_index(drop=True)
    window.insert(0, "Timestamp", [start + pd.Timedelta(minutes=i) for i in range(len(window))])
    return window, validate_window(window)


def read_csv_window(data, max_bytes=MAX_CSV_BYTES):
    """CSV bytes -> (window DataFrame of the LAST 5 rows, info dict). Raises InputFileError if it is not a readable table.
    Header spaces are trimmed; columns other than Timestamp and the 7 features are ignored. Nothing else is changed."""
    if len(data) > max_bytes:
        raise InputFileError("FILE_TOO_LARGE", f"the file is {len(data) / 1e6:.1f} MB; the limit is {max_bytes / 1e6:.0f} MB")
    try:
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
        raise InputFileError("BAD_CSV", f"the file could not be read as a CSV table ({type(e).__name__})")
    df.columns = [str(c).strip() for c in df.columns]
    keep = (["Timestamp"] if "Timestamp" in df.columns else []) + [c for c in FEATURES if c in df.columns]
    if not keep:
        shown = ", ".join(f"'{c}'" for c in df.columns[:4]) + (" ..." if len(df.columns) > 4 else "")
        raise InputFileError("BAD_CSV", f"none of the expected column names were found (the file's columns: {shown})")
    info = {"total_rows": len(df), "used_rows": min(len(df), WINDOW_ROWS), "has_timestamp": "Timestamp" in df.columns,
            "ignored_columns": [c for c in df.columns if c not in keep]}
    return df[keep].tail(WINDOW_ROWS).reset_index(drop=True), info


# Illustrative examples for trying the dashboard. They are NOT real traffic.
def _example(bot, flows, fp, bp, fb, bb, dur):
    return pd.DataFrame({"Bot_Pct": [float(b) for b in bot], "Total_Flows": [float(flows)] * 5, "Fwd_Pkts_Bot": [float(fp)] * 5,
                         "Bwd_Pkts_Bot": [float(bp)] * 5, "Fwd_Bytes_Bot": [float(fb)] * 5, "Bwd_Bytes_Bot": [float(bb)] * 5,
                         "Avg_Duration_Bot": [float(dur)] * 5})[FEATURES]


def presets():
    return {
        "Quiet traffic (example)": _example([3, 4, 2, 3, 4], 400, 200, 150, 10000, 5000, 5000),
        "Typical traffic (example)": _example([18, 19, 17, 18, 18], 1825, 1100, 850, 65000, 30000, 23000),
        "Busy traffic (example)": _example([45, 50, 55, 52, 56], 3000, 2500, 2000, 150000, 80000, 60000),
    }
