"""All wording shown to the user, kept in one place so the safety wording stays consistent.
Wording rules (docs/FRONTEND_HANDOFF.md and docs/EXPLAINABILITY.md): offline/batch only, never real-time detection,
a Low or Medium state is never proof of safe traffic, and seed spread is called "Model Disagreement"."""

APP_TITLE = "SIH26153: Bot Traffic Forecast Dashboard"
APP_SUBTITLE = "Forecasts the bot share of network traffic for the next minute from the last 5 minutes of data."

PROVISIONAL_BANNER = ("PROVISIONAL model. Offline, batch forecast only. This is not a real-time detector, and a forecast "
                      "is an estimate of traffic state, not proof of an attack.")
LOW_RECALL_NOTE = ("Low-state recall was about 0% on the test day. A Low or Medium forecast must not be taken as proof "
                   "that traffic is safe.")
DEMO_BANNER = ("DEMO MODE: no backend was contacted. The values below are placeholders from the API contract, "
               "used only to test the screens. They are not model forecasts.")
MOCK_BANNER = ("SIMULATION MODE ACTIVE: the backend is running in MOCK mode. Forecast values are placeholder stubs "
               "for testing the layout only.")
MOCK_TAG = " [MOCK]"

LIMITATIONS = [
    "Offline and batch only: works on pre-aggregated 1-minute records. It is not a packet inspection engine.",
    "Benchmark scope: evaluated on 102 target windows from a single day of CSE-CIC-IDS2018.",
    "Macro state forecasting: predicts the overall percentage of bot flows, not individual attackers or packets.",
    "Low-state blind spot: Low-state recall was about 0% on the test day, so Low and Medium forecasts do not prove safety.",
]

# User-friendly text for every error_code the backend or this client can raise (docs/FRONTEND_HANDOFF.md section 6).
ERROR_MESSAGES = {
    "MISSING_FEATURES": "Missing required traffic columns. Ensure all 7 features are included.",
    "BAD_SHAPE": "Window must contain exactly 5 rows of traffic data.",
    "NAN_OR_INF": "Data contains invalid empty (NaN) or infinite values. Please check table cells.",
    "NEGATIVE_VALUE": "Negative values are invalid for traffic counts, bytes, or durations.",
    "BOT_PCT_RANGE": "Bot percentage must be between 0.0% and 100.0%.",
    "BAD_TIMESTAMP": "Invalid timestamp format. Use standard YYYY-MM-DD HH:MM:SS.",
    "NOT_CONSECUTIVE": "Time gap detected! Sequence rows must be exactly 60 seconds apart.",
    "BAD_REQUEST": "The request was not in the expected format (a JSON object with a 'window' list).",
    "SERVER_ERROR": "Backend service encountered an error. Please verify backend logs.",
    "BACKEND_UNREACHABLE": "Cannot reach the backend at the address in the sidebar. Check that it is running, "
                           "or switch on Demo mode to test the screens without a backend.",
    "BACKEND_TIMEOUT": "The backend did not answer in time. Check that it is running and try again.",
    "BAD_URL": "The backend address in the sidebar is not valid.",
    "BAD_INPUT": "The traffic window could not be read. Check the table or file and try again.",
    "BAD_RESPONSE": "The backend answered, but not in the format the API contract defines, so the result was not shown.",
    "NOT_NUMERIC": "A cell that should hold a number contains text. Please enter numbers only.",
    "BAD_CSV": "The file could not be read as a CSV table. Check that it is a comma-separated .csv file.",
    "FILE_TOO_LARGE": "The file is too large. Upload a smaller CSV (only the last 5 rows are used).",
    "REQUEST_FAILED": "The request to the backend failed. Check the address and your network.",
}


def describe_error(err):
    """One user-facing message for an ApiError (friendly text first, then the technical detail if it adds anything)."""
    friendly = ERROR_MESSAGES.get(err.code)
    if friendly is None:
        friendly = f"The backend returned an unexpected error (HTTP {err.http_status})." if err.http_status \
            else "An unexpected error occurred."
    if err.message and err.message != friendly:
        return f"{friendly}\n\nDetails: {err.message}"
    return friendly


# ---------------------------------------------------------------------------------------------------------------------
# Phase 4: navigation and the "About the model" page. Facts come from docs/FINAL_REPORT_MEMBER3.md sections 3 and 10.
# ---------------------------------------------------------------------------------------------------------------------
NAV_FORECAST = "Forecast dashboard"
NAV_ABOUT = "About the model"
NAV_PAGES = [NAV_FORECAST, NAV_ABOUT]

ABOUT_TITLE = "About the model"
ABOUT_INTRO = (
    "This prototype forecasts the share of network traffic that comes from bots for the NEXT minute, using the last 5 "
    "minutes of pre-aggregated traffic records. It estimates a traffic state (Low, Medium or High). It does not detect "
    "individual attacks, attackers or packets, and it is not a real-time system."
)
ABOUT_HOW = [
    "You supply 5 consecutive one-minute records, 60 seconds apart, each with 7 traffic features.",
    "This page sends them to the backend. The model never runs in the browser.",
    "The backend checks the data, then 5 LSTM models (an ensemble, seeds 42 to 46) each make a forecast.",
    "The average of the 5 forecasts is shown as the predicted bot traffic share (limited to 0 to 100%).",
    "The state follows from that percentage: Low below 25%, Medium from 25% to below 50%, High at 50% or above.",
    "Model Disagreement is how far apart the 5 forecasts are. It shows how much the models differ. It is not an error "
    "margin and not a statistical guarantee.",
]
ABOUT_FEATURES = [   # (feature, plain meaning). Units of Avg_Duration_Bot are not confirmed in the project documents.
    ("Bot_Pct", "Share of the minute's network flows that are bot flows, from 0 to 100."),
    ("Total_Flows", "Number of all network flows in the minute."),
    ("Fwd_Pkts_Bot", "Forward packets in the bot flows."),
    ("Bwd_Pkts_Bot", "Backward packets in the bot flows."),
    ("Fwd_Bytes_Bot", "Forward bytes in the bot flows."),
    ("Bwd_Bytes_Bot", "Backward bytes in the bot flows."),
    ("Avg_Duration_Bot", "Average duration of the bot flows (unit not confirmed in the project documents)."),
]
ABOUT_STATES = [
    ("Low", "below 25% bot traffic"),
    ("Medium", "25% to below 50% bot traffic"),
    ("High", "50% bot traffic or above"),
]
ABOUT_METRICS_NOTE = (
    "Measured on 102 forecast targets from a single day of CSE-CIC-IDS2018. One day is a small test: results on other "
    "days or other networks are unknown. The model is PROVISIONAL."
)
# (metric, LSTM ensemble, 'same as last minute' baseline). Copied from FINAL_REPORT_MEMBER3.md section 3.2.
ABOUT_METRICS = [
    ("Mean absolute error (points of bot share, lower is better)", "6.92", "9.31"),
    ("Root mean squared error (points, lower is better)", "8.43", "11.67"),
    ("R squared (higher is better)", "0.62", "0.27"),
    ("Share of test forecasts with the correct state", "71.57% (73 of 102)", "59.80% (61 of 102)"),
    ("High state recall", "92.31% (12 of 13)", "61.54% (8 of 13)"),
    ("Medium state recall", "92.42% (61 of 66)", "74.24% (49 of 66)"),
    ("Low state recall", "0.00% (0 of 23)", "17.39% (4 of 23)"),
]
ABOUT_LOW_RECALL = (
    "All 23 Low targets on the test day were forecast as Medium. A Medium forecast therefore does not rule out Low "
    "traffic, and neither Low nor Medium proves that traffic is safe."
)
ABOUT_LIMITATIONS = LIMITATIONS + [
    "Single-day evaluation: how well it works on other days or networks has not been shown.",
    "Model Disagreement is not an error margin: it measures how much the 5 models differ, not how likely a forecast is to be right.",
    "Regenerated model package: retrained from the saved configuration. It reproduces the saved test metrics to within 0.001 points but is not byte-identical to the original files.",
]
