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
