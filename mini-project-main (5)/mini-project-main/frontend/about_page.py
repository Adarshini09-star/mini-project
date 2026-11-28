"""The 'About the model' page (Phase 4). Pure display of the text in ui_text.py: no model code, no backend calls,
no numbers computed here. Every figure comes from docs/FINAL_REPORT_MEMBER3.md via ui_text.py."""
import pandas as pd
import streamlit as st

import ui_text as T


def render():
    st.header(T.ABOUT_TITLE)
    st.write(T.ABOUT_INTRO)
    how, inputs, evaluation, limits = st.tabs(["How it works", "Inputs and states", "Test results", "Limitations"])
    with how:
        for i, step in enumerate(T.ABOUT_HOW, start=1):
            st.write(f"{i}. {step}")
    with inputs:
        st.markdown("**The 7 input features (one row per minute, 5 rows)**")
        st.dataframe(pd.DataFrame(T.ABOUT_FEATURES, columns=["Feature", "Meaning"]), hide_index=True)
        st.markdown("**Estimated traffic states**")
        st.dataframe(pd.DataFrame(T.ABOUT_STATES, columns=["State", "Predicted bot share"]), hide_index=True)
    with evaluation:
        st.info(T.ABOUT_METRICS_NOTE, icon="ℹ️")
        st.dataframe(pd.DataFrame(T.ABOUT_METRICS, columns=["Measure", "LSTM ensemble", "Baseline: same as last minute"]),
                     hide_index=True)
        st.warning(T.ABOUT_LOW_RECALL, icon="⚠️")
    with limits:
        st.warning(T.PROVISIONAL_BANNER, icon="⚠️")
        for item in T.ABOUT_LIMITATIONS:
            st.write("• " + item)
