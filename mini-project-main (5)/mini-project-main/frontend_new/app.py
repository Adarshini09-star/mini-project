"""SIH26153 dashboard, Phase 4: Forecast, Traffic Analytics and About the Model sections.
The user types or uploads the last 5 minutes of traffic, the app checks it (validation.py), and only valid data can be sent
to the backend (api_client.py). Everything shown about the forecast comes from the backend response (display.py).

The decorative banner (hero_banner.py) and the cream / black switch (theme_switch.py) are drawn at the top.

Run from inside this folder:   python -m streamlit run app.py
"""
import pandas as pd
import streamlit as st

import api_client as api
import display as D
import hero_banner
import theme_switch as TS
import ui_text as T
import validation as V

st.set_page_config(page_title="Bot Traffic Forecast", page_icon="📈", layout="wide")

PRESETS = V.presets()
ROW_LABELS = ["Minute 1 (oldest)", "Minute 2", "Minute 3", "Minute 4", "Minute 5 (newest)"]


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def line_chart(frame):
    st.line_chart(frame, color=D.chart_colors(frame))


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
    elif result["ok"] and api.is_mock(result["data"]):
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


def input_signature(window):
    """What a forecast was made from: the window AND the settings (Demo mode, backend address). None if there is no valid window."""
    if window is None:
        return None
    return f"{demo}|{base_url}|{window.to_json(date_format='iso')}"


def is_placeholder(result):
    return result["demo"] or (result["ok"] and api.is_mock(result["data"]))


def show_forecast_card(result):
    if not result["ok"]:
        st.error(T.describe_error(result["error"]))
        return
    f = result["data"]
    html(D.card_html(f, placeholder=is_placeholder(result)))
    st.info(T.STATE_NOTICE[f["predicted_state"]])


def show_details(result, window):
    """Lower part of the page: uncertainty, charts, explanations and advisories for a successful forecast."""
    f, placeholder = result["data"], is_placeholder(result)
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Uncertainty and explanations")
        html(D.gauge_html(f["seed_spread_pct_points"]))
        st.markdown("**Ensemble seed predictions**")
        st.bar_chart(D.seed_series(f))
        st.caption(D.seed_caption(f))
        st.markdown("**Historical observed traffic and forecast (t+1 min)**")
        line_chart(D.observed_vs_forecast_frame(window, f["predicted_bot_pct_next_minute"]))
        st.caption("Observed values are the 5 input minutes. The forecast is the model's estimate for the next minute, not an observation."
                   + (" The forecast line shows placeholder values." if placeholder else ""))
        st.markdown("**What the numbers show**")
        if placeholder:
            st.caption("Not shown for placeholder values.")
        else:
            for line in D.describe_forecast(window, f):
                st.write("• " + line)
            st.caption("These statements describe the input and the response. They do not show how the neural network reached its estimate.")
    with right:
        st.subheader("System advisories")
        for w in f["warnings"]:
            st.warning(w, icon="⚠️")
        st.info(T.LOW_RECALL_NOTE)
        with st.expander("Model diagnostics (raw API response)"):
            st.json(f)


def show_analytics(window, source):
    """Traffic Analytics: summary cards, charts and tables for the 5 minutes of input (never model output)."""
    st.caption(source)
    n, latest = len(window), window.iloc[-1]
    prev = window.iloc[-2] if n > 1 else None

    def card(col, name):
        delta = None if prev is None else D.change_text(name, latest[name], prev[name])
        col.metric(D.LABEL[name], D.format_value(name, latest[name]), delta=delta, delta_color="off")

    c = st.columns(4)
    card(c[0], "Bot_Pct")
    c[1].metric("Observed state (newest minute)", D.observed_state(float(latest["Bot_Pct"])))
    card(c[2], "Total_Flows")
    card(c[3], "Avg_Duration_Bot")
    c = st.columns(4)
    for col, name in zip(c, ["Fwd_Pkts_Bot", "Bwd_Pkts_Bot", "Fwd_Bytes_Bot", "Bwd_Bytes_Bot"]):
        card(col, name)
    st.caption("Newest minute, with the change from the minute before. " + T.ANALYTICS_NOTE)

    left, right = st.columns(2)
    with left:
        st.markdown("**Bot share over the 5 minutes (%)**")
        line_chart(D.series_frame(window, ["Bot_Pct"], thresholds=True))
        st.markdown("**Forward and backward packets (bot flows)**")
        line_chart(D.series_frame(window, ["Fwd_Pkts_Bot", "Bwd_Pkts_Bot"]))
        st.markdown("**Average duration of bot flows (unit not confirmed)**")
        line_chart(D.series_frame(window, ["Avg_Duration_Bot"]))
    with right:
        st.markdown("**Total flows per minute**")
        line_chart(D.series_frame(window, ["Total_Flows"]))
        st.markdown("**Forward and backward bytes (bot flows)**")
        line_chart(D.series_frame(window, ["Fwd_Bytes_Bot", "Bwd_Bytes_Bot"]))
        st.markdown("**Observed state of each minute**")
        st.dataframe(D.state_table(window), hide_index=True)
        st.caption(T.OBSERVED_STATE_NOTE)
    st.markdown("**Summary of the 5 minutes**")
    st.dataframe(D.analytics_summary_display(window))


def show_about():
    for heading, body in T.ABOUT_SECTIONS:
        st.subheader(heading)
        st.markdown(body)
    st.subheader("The 7 input features")
    st.markdown(D.feature_table_markdown())
    st.caption(T.ABOUT_DOC_NOTE)
    st.subheader("Limitations")
    for item in T.LIMITATIONS:
        st.write("• " + item)


hero_banner.render()   # decorative moving-characters banner (hero_banner.py); never shows forecast values
st.title(T.APP_TITLE)
st.caption(T.APP_SUBTITLE)
st.warning(T.PROVISIONAL_BANNER)

# Page style switch: cream (light) or black. Starts in whatever theme the page is showing now.
if "black_mode" not in st.session_state:
    st.session_state["black_mode"] = (st.context.theme.type == "dark")


def _theme_changed():
    st.session_state["theme_switch"] = "dark" if st.session_state["black_mode"] else "light"


st.sidebar.toggle("Black background (off = light cream)", key="black_mode", on_change=_theme_changed)
TS.render(switch_to=st.session_state.pop("theme_switch", None))

banner_slot = st.container()          # filled further down, once the latest forecast is known

demo = st.sidebar.toggle("Demo mode (no backend)", value=False,
                         help="Shows placeholder values from the API contract so the screens can be tested without a backend.")
base_url = st.sidebar.text_input("Backend address", value=api.DEFAULT_BASE_URL, disabled=demo)
if demo:
    st.sidebar.caption("Demo mode is ON: no backend is contacted and results are placeholders.")

tab_forecast, tab_analytics, tab_about = st.tabs(["Forecast", "Traffic Analytics", "About the Model"])

with tab_forecast:
    st.subheader("1. Backend connection")
    if st.button("Check backend connection"):
        with st.spinner("Contacting the backend..."):
            st.session_state["health_result"] = call(lambda: api.fetch_health(base_url, demo=demo), demo)
    if "health_result" in st.session_state:
        show_health(st.session_state["health_result"])

    input_col, forecast_col = st.columns([3, 2])
    with input_col:
        st.subheader("2. Input window (last 5 minutes)")
        window, issues = read_input()
        ready = window is not None and not issues
        if issues:
            show_issues(issues)
        elif window is not None:
            st.success("Input looks valid: 5 rows, 7 features, rows 60 seconds apart.")
            st.dataframe(window, hide_index=True)
        if st.button("Get forecast", type="primary", disabled=not ready):
            with st.spinner("Waiting for the forecast..."):
                st.session_state["forecast_result"] = call(lambda: api.request_forecast(window, base_url, demo=demo), demo)
                st.session_state["forecast_window"] = window.copy()
                st.session_state["forecast_input"] = input_signature(window)

    result = st.session_state.get("forecast_result")
    with forecast_col:
        st.subheader("3. Next-minute forecast (t+1)")
        if result is None:
            st.caption("No forecast yet. Enter valid data and click Get forecast." if not ready else "No forecast yet. Click Get forecast.")
        else:
            if st.session_state.get("forecast_input") != input_signature(window):
                st.info("This forecast was made from earlier input values or settings. Click Get forecast to update it.")
            show_forecast_card(result)

    with banner_slot:
        if result is not None:
            show_status_banner(result)

    if result is not None and result["ok"]:
        show_details(result, st.session_state["forecast_window"])


with tab_analytics:
    st.subheader("Traffic analytics (5-minute input window)")
    if window is not None and not issues:
        show_analytics(window, "Showing the input window currently entered in the Forecast section.")
    elif st.session_state.get("forecast_window") is not None:
        show_analytics(st.session_state["forecast_window"], "The current input is not valid. Showing the window used for the latest forecast.")
    else:
        st.info("No traffic data yet. Enter a valid 5-minute window in the Forecast section to see analytics here.")

with tab_about:
    show_about()

st.divider()
st.caption(T.LOW_RECALL_NOTE)
with st.expander("Limitations of this prototype"):
    for item in T.LIMITATIONS:
        st.write("• " + item)
st.caption(T.FOOTER)
