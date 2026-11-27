"""SIH26153 dashboard, Phase 4: navigation + backend check + traffic data input + forecast request + full forecast display.
The user types or uploads the last 5 minutes of traffic, the app checks it (validation.py), and only valid data can be sent
to the backend (api_client.py). The result is shown by display.py helpers (forecast card, observed-vs-forecast chart, model disagreement, warnings).

Run from inside this folder:   python -m streamlit run app.py
"""
import streamlit as st

import about_page
import api_client as api
import display as DP
import page_background as PB
import ui_text as T
import validation as V

st.set_page_config(page_title="Bot Traffic Forecast", page_icon="📈", layout="wide")

PRESETS = V.presets()
# Column order of display.observed_vs_forecast_frame: observed, forecast, Medium line, High line.
CHART_COLORS = ["#6FA06B", "#5B8DB8", "#E0B565", "#C98383"]
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


def show_forecast(result, window=None):
    """Phase 3 display. `window` is the 5-row input that produced this forecast (used for the observed-vs-forecast chart)."""
    if not result["ok"]:
        st.error(T.describe_error(result["error"]))
        return
    f = result["data"]
    show_status_banner(result)
    placeholder = bool(result["demo"] or api.is_mock(f))
    left, right = st.columns([1, 1])
    with left:
        st.markdown(DP.card_html(f, placeholder=placeholder), unsafe_allow_html=True)
        st.info(T.LOW_RECALL_NOTE, icon="ℹ️")
    with right:
        st.markdown(f'<div style="background:{DP.CARD_BG};border:1px solid {DP.BORDER};border-radius:12px;padding:14px 16px;">'
                    + DP.gauge_html(f["seed_spread_pct_points"]) + "</div>", unsafe_allow_html=True)
        if placeholder:
            st.info("Placeholder values: the disagreement shown here is not from a real model run.", icon="ℹ️")
    if window is not None:
        st.markdown("**Observed input window and forecast**")
        st.caption("Observed = the 5 minutes you entered. Forecast (t+1) = the backend model's estimate for the next minute.")
        if placeholder:
            st.info("The forecast point (t+1) in this chart is a placeholder, not a model forecast.", icon="ℹ️")
        st.line_chart(DP.observed_vs_forecast_frame(window, f["predicted_bot_pct_next_minute"]),
                      color=CHART_COLORS,
                      x_label="Minute relative to the newest row (t)", y_label="Bot share of traffic (%)")
        if not placeholder:
            for line in DP.describe_forecast(window, f):
                st.write("• " + line)
    if f["warnings"]:
        st.markdown("**Model advisories**")
        for w in f["warnings"]:
            st.warning(w, icon="⚠️")
    with st.expander("Model Diagnostics: the 5 individual model forecasts"):
        st.caption("Each of the 5 ensemble models (seeds) gives its own forecast; their spread is the Model Disagreement.")
        st.bar_chart(DP.seed_series(f), y_label="Predicted bot share (%)")
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

# Navigation (Phase 4). Both pages share the title, the PROVISIONAL banner and the sidebar.
st.sidebar.radio("Section", T.NAV_PAGES, key="nav_page")

# Page style switch: cream (light) or black. Starts in whatever theme the page is showing now.
if "black_mode" not in st.session_state:
    st.session_state["black_mode"] = (st.context.theme.type == "dark")


def _theme_changed():
    st.session_state["theme_switch"] = "dark" if st.session_state["black_mode"] else "light"


st.sidebar.toggle("Black background (off = light cream)", key="black_mode", on_change=_theme_changed)
PB.render(dark=st.session_state["black_mode"], switch_to=st.session_state.pop("theme_switch", None))

demo = st.sidebar.toggle("Demo mode (no backend)", value=False,
                         help="Shows placeholder values from the API contract so the screens can be tested without a backend.")
base_url = st.sidebar.text_input("Backend address", value=api.DEFAULT_BASE_URL, disabled=demo)
if demo:
    st.sidebar.caption("Demo mode is ON: no backend is contacted and results are placeholders.")

if st.session_state["nav_page"] == T.NAV_ABOUT:
    about_page.render()
    st.divider()
    st.caption(T.LOW_RECALL_NOTE)
    st.stop()

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
        st.session_state["forecast_window"] = window.copy()
if "forecast_result" in st.session_state:
    if st.session_state.get("forecast_input") != (window.to_json(date_format="iso") if window is not None else None):
        st.info("The forecast below was made from earlier input values. Click Get forecast to update it.")
    show_forecast(st.session_state["forecast_result"], st.session_state.get("forecast_window"))
else:
    st.caption("No forecast yet. Enter valid data above and click Get forecast." if not ready else "No forecast yet. Click Get forecast.")

st.divider()
st.caption(T.LOW_RECALL_NOTE)
with st.expander("Limitations of this prototype"):
    for item in T.LIMITATIONS:
        st.write("• " + item)
