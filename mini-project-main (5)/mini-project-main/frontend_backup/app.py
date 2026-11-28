"""SIH26153 dashboard, Phase 1: connection test.
Checks the backend (GET /health) and sends one made-up sample window (POST /predict) so the API client can be verified.
The full dashboard (input table, forecast card, analytics) is built on top of this in later phases.

Run from inside this folder:   python -m streamlit run app.py
"""
import streamlit as st

import api_client as api
import ui_text as T

st.set_page_config(page_title="Bot Traffic Forecast", page_icon="📈", layout="wide")

# Made-up numbers for a connection test only (the example window from docs/API_CONTRACT.md). Not real traffic.
SAMPLE_WINDOW = [
    {"Timestamp": "2018-02-03T09:00:00", "Bot_Pct": 18.0, "Total_Flows": 1800, "Fwd_Pkts_Bot": 1050, "Bwd_Pkts_Bot": 820,
     "Fwd_Bytes_Bot": 63000, "Bwd_Bytes_Bot": 28000, "Avg_Duration_Bot": 22000},
    {"Timestamp": "2018-02-03T09:01:00", "Bot_Pct": 19.5, "Total_Flows": 1850, "Fwd_Pkts_Bot": 1100, "Bwd_Pkts_Bot": 860,
     "Fwd_Bytes_Bot": 66000, "Bwd_Bytes_Bot": 30000, "Avg_Duration_Bot": 23000},
    {"Timestamp": "2018-02-03T09:02:00", "Bot_Pct": 17.2, "Total_Flows": 1790, "Fwd_Pkts_Bot": 1020, "Bwd_Pkts_Bot": 800,
     "Fwd_Bytes_Bot": 61000, "Bwd_Bytes_Bot": 27500, "Avg_Duration_Bot": 21500},
    {"Timestamp": "2018-02-03T09:03:00", "Bot_Pct": 20.1, "Total_Flows": 1900, "Fwd_Pkts_Bot": 1150, "Bwd_Pkts_Bot": 890,
     "Fwd_Bytes_Bot": 68000, "Bwd_Bytes_Bot": 31000, "Avg_Duration_Bot": 24000},
    {"Timestamp": "2018-02-03T09:04:00", "Bot_Pct": 18.8, "Total_Flows": 1830, "Fwd_Pkts_Bot": 1080, "Bwd_Pkts_Bot": 840,
     "Fwd_Bytes_Bot": 65000, "Bwd_Bytes_Bot": 29500, "Avg_Duration_Bot": 22500},
]


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
    placeholder = result["demo"] or api.is_mock(f)
    tag = T.MOCK_TAG if placeholder else ""
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted bot traffic (next minute)", f"{f['predicted_bot_pct_next_minute']:.2f} %{tag}")
    c2.metric("Estimated traffic state", f"{f['predicted_state']}{tag}")
    c3.metric("Model disagreement (points)", f"{f['seed_spread_pct_points']:.2f}")
    for w in f["warnings"]:
        st.warning(w)
    with st.expander("Raw response from the API"):
        st.json(f)


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

st.subheader("2. Connection test with a sample window")
st.caption("Sends 5 made-up example rows (not real traffic) to POST /predict to check that the API client works end to end.")
if st.button("Send sample window"):
    with st.spinner("Waiting for the forecast..."):
        st.session_state["forecast_result"] = call(lambda: api.request_forecast(SAMPLE_WINDOW, base_url, demo=demo), demo)
if "forecast_result" in st.session_state:
    show_forecast(st.session_state["forecast_result"])

st.divider()
st.caption(T.LOW_RECALL_NOTE)
with st.expander("Limitations of this prototype"):
    for item in T.LIMITATIONS:
        st.write("• " + item)
