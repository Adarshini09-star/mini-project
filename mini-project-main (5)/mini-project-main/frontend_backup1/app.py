"""SIH26153 dashboard, Phase 2: backend check + traffic data input + forecast request.
The user types or uploads the last 5 minutes of traffic, the app checks it (validation.py), and only valid data can be sent
to the backend (api_client.py). The result is shown in a simple form here; Phase 3 turns it into the full forecast display.

Run from inside this folder:   python -m streamlit run app.py
"""
import streamlit as st

import api_client as api
import ui_text as T
import validation as V

st.set_page_config(page_title="Bot Traffic Forecast", page_icon="📈", layout="wide")

PRESETS = V.presets()
ROW_LABELS = ["Minute 1 (oldest)", "Minute 2", "Minute 3", "Minute 4", "Minute 5 (newest)"]


def call(fn, demo):
    """Run an API call and keep either its result or its error, plus whether it was a demo call."""
    try:
        return {"ok": True, "data": fn(), "demo": demo}
    except api.ApiError as e:
        return {"ok": False, "error": e, "demo": demo}


def show_status_banner(result):
    """Placeholder values must never look like forecasts: demo and MOCK results always get a banner."""
    if result["demo"]:
        st.error(T.DEMO_BANNER)
    elif api.is_mock(result["data"]):
        st.error(T.MOCK_BANNER)


def show_health(result):
    if not result["ok"]:
        st.error(T.describe_error(result["error"]))
        return
    h = result["data"]
    show_status_banner(result)
    c1, c2, c3 = st.columns(3)
    c1.metric("Backend status", "Demo (none)" if result["demo"] else str(h["status"]))
    c2.metric("Model version", str(h["model_version"]))
    c3.metric("Model status", str(h["model_status"]))
    for item in h["limitations"]:
        st.write("• " + str(item))


def show_forecast(result):
    if not result["ok"]:
        st.error(T.describe_error(result["error"]))
        return
    f = result["data"]
    show_status_banner(result)
    tag = T.MOCK_TAG if (result["demo"] or api.is_mock(f)) else ""
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted bot traffic (next minute)", f"{f['predicted_bot_pct_next_minute']:.2f} %{tag}")
    c2.metric("Estimated traffic state", f"{f['predicted_state']}{tag}")
    c3.metric("Model disagreement (points)", f"{f['seed_spread_pct_points']:.2f}")
    for w in f["warnings"]:
        st.warning(w)
    with st.expander("Raw response from the API"):
        st.json(f)


def show_issues(issues):
    for i in issues:
        st.error(f"{T.ERROR_MESSAGES.get(i.code, 'There is a problem with the input.')}\n\nDetails: {i.detail}")


def read_input():
    """Draw the input widgets. Returns (window DataFrame or None, list of Issue)."""
    method = st.radio("Input method", ["Type or edit values", "Upload a CSV file"], horizontal=True)
    if method.startswith("Type"):
        preset = st.selectbox("Start from an example (made-up numbers, not real traffic; every value can be edited)", list(PRESETS))
        start = st.text_input("Time label of the first (oldest) row", value=V.DEFAULT_START,
                              help="Only labels the minutes so the backend can check they are 60 seconds apart. Format: YYYY-MM-DD HH:MM:SS")
        st.write("One row is one minute, oldest at the top. The forecast is for the minute after the last row.")
        table = st.data_editor(PRESETS[preset].set_axis(ROW_LABELS), num_rows="fixed", key="editor_" + preset)
        return V.table_to_window(table, start)
    st.write("CSV columns: Timestamp (recommended), " + ", ".join(V.FEATURES) + ". The LAST 5 rows are used; other columns are ignored.")
    up = st.file_uploader("CSV file", type="csv")
    if up is None:
        st.info("Choose a CSV file to continue.")
        return None, []
    try:
        window, info = V.read_csv_window(up.getvalue())
    except V.InputFileError as e:
        return None, [V.Issue(e.code, e.detail)]
    st.caption(f"Read {info['total_rows']} rows; using the last {info['used_rows']}."
               + (f" Ignored columns: {', '.join(info['ignored_columns'])}." if info["ignored_columns"] else ""))
    if not info["has_timestamp"]:
        st.warning("No Timestamp column: the backend cannot check that the rows are 60 seconds apart.")
    return window, V.validate_window(window)


st.title(T.APP_TITLE)
st.caption(T.APP_SUBTITLE)
st.warning(T.PROVISIONAL_BANNER)

demo = st.sidebar.toggle("Demo mode (no backend)", value=False,
                         help="Shows placeholder values from the API contract so the screens can be tested without a backend.")
base_url = st.sidebar.text_input("Backend address", value=api.DEFAULT_BASE_URL, disabled=demo)
if demo:
    st.sidebar.caption("Demo mode is ON: no backend is contacted and results are placeholders.")

st.subheader("1. Backend connection")
if st.button("Check backend connection"):
    with st.spinner("Contacting the backend..."):
        st.session_state["health_result"] = call(lambda: api.fetch_health(base_url, demo=demo), demo)
if "health_result" in st.session_state:
    show_health(st.session_state["health_result"])

st.subheader("2. Traffic data")
window, issues = read_input()
ready = window is not None and not issues
if issues:
    show_issues(issues)
elif window is not None:
    st.success("Input looks valid: 5 rows, 7 features, rows 60 seconds apart.")
    st.dataframe(window)

st.subheader("3. Forecast")
if st.button("Get forecast", type="primary", disabled=not ready):
    with st.spinner("Waiting for the forecast..."):
        st.session_state["forecast_result"] = call(lambda: api.request_forecast(window, base_url, demo=demo), demo)
        st.session_state["forecast_input"] = window.to_json(date_format="iso")
if "forecast_result" in st.session_state:
    if st.session_state.get("forecast_input") != (window.to_json(date_format="iso") if window is not None else None):
        st.info("The forecast below was made from earlier input values. Click Get forecast to update it.")
    show_forecast(st.session_state["forecast_result"])
else:
    st.caption("No forecast yet. Enter valid data above and click Get forecast." if not ready else "No forecast yet. Click Get forecast.")

st.divider()
st.caption(T.LOW_RECALL_NOTE)
with st.expander("Limitations of this prototype"):
    for item in T.LIMITATIONS:
        st.write("• " + item)
