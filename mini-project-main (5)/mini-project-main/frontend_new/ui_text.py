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

FOOTER = "SIH26153 research prototype. Evaluated on the CSE-CIC-IDS2018 benchmark. Offline, batch forecasts only."

ANALYTICS_NOTE = ("Analytics describe the 5 input minutes you entered. They are observations from your input, not model output "
                  "and not live traffic. The unit of the average duration is not confirmed yet, so it is shown as given.")
OBSERVED_STATE_NOTE = ("Observed state applies the same Low / Medium / High thresholds to the observed bot share of each minute. "
                       "It is not a model prediction.")

# About the Model page: (heading, markdown). Facts come from docs/ARCHITECTURE.md, PREPROCESSING.md and API_CONTRACT.md.
ABOUT_SECTIONS = [
    ("What this dashboard does",
     "It asks a backend service for a forecast of the **bot share of network traffic in the next minute**, using the last "
     "5 one-minute records, and shows the result with its warnings. It is a research prototype built for the SIH26153 project."),
    ("How the forecast is made",
     "- **Input:** 5 consecutive one-minute records (60 seconds apart) with 7 features each.\n"
     "- **Model:** an ensemble of 5 LSTM networks trained with different random seeds (42 to 46). The forecast is their combined output.\n"
     "- **Output:** the predicted bot share for the next minute, turned into a state: **Low** (below 25%), **Medium** (25% to below 50%) "
     "or **High** (50% or above).\n"
     "- **Where it runs:** in the backend only. This dashboard never loads the model; it only sends the 5 rows and shows the answer."),
    ("How to read the screen",
     "- **Estimated traffic state:** the state of the forecast bot share. It is an estimate, not a finding about individual traffic.\n"
     "- **Model Disagreement:** how far apart the 5 models are, in percentage points. It tells you how much the models differ; "
     "it does not tell you how likely the forecast is to be right.\n"
     "- **[MOCK] tags and red banners:** placeholder values used for testing the screens. They are never real forecasts."),
    ("What it does not do",
     "- It is **not real-time**: it works on prepared one-minute records, offline.\n"
     "- It does **not detect or prove attacks** and does not look at individual packets or senders.\n"
     "- A **Low or Medium forecast is not proof that traffic is safe.** Low-state recall was about 0% on the test day.\n"
     "- It was evaluated on 102 target windows from a single day of the CSE-CIC-IDS2018 benchmark, so treat it as provisional."),
]
ABOUT_DOC_NOTE = ("Feature meanings are taken from the project documentation (docs/PREPROCESSING.md). The exact definition of Bot_Pct "
                  "and the unit of Avg_Duration_Bot are still to be confirmed by the dataset team.")

# Shown under the forecast card for the forecast state. The Low notice is the wording required by docs/FRONTEND_HANDOFF.md.
STATE_NOTICE = {
    "Low": "Notice: Low-state recall is about 0% on test benchmarks. Low predictions are subject to a high risk of missed bot traffic (false negatives).",
    "Medium": "A Medium forecast is an estimate. It does not show that traffic is safe, and it does not rule out Low or High bot traffic.",
    "High": "A High forecast means the model expects half or more of the traffic to be bot-related. It is an estimate, not confirmation of an attack.",
}

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
