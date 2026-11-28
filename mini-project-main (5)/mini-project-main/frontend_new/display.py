"""Pure helpers that turn a forecast response into what the dashboard shows (Phase 3).

Wording follows docs/FRONTEND_HANDOFF.md: seed spread is called "Model Disagreement", states are estimates of bot share
(never "attack detected"), and the traffic state shown is always the backend's `predicted_state`. It is never recomputed here.
No Streamlit and no model code in this file, so it can be unit-tested.
"""
import html

import pandas as pd

from ui_text import MOCK_TAG

INK, MUTED, CARD_BG, BORDER = "#2E2B28", "#6B5D4F", "#FFFDF8", "#D9D0BC"
TREND_DELTA = 5.0        # points of change in bot share over the 5 minutes before it is called rising or falling
GAUGE_MAX = 15.0         # the disagreement gauge runs from 0 to 15 points (anything above is shown at the right edge)

STATE_STYLE = {
    "Low": {"label": "LOW", "range": "below 25% bot", "sub": "Lower bot share forecast", "accent": "#3F6B3A"},
    "Medium": {"label": "MEDIUM", "range": "25% to below 50% bot", "sub": "Elevated bot share forecast", "accent": "#9A6700"},
    "High": {"label": "HIGH", "range": "50% bot or above", "sub": "High bot share forecast", "accent": "#A63D40"},
}
DISAGREEMENT = (            # (upper limit in percentage points, level, meaning, colour), limits from the hand-off section 4.3
    (5.0, "Low", "The 5 models agree closely.", "#3F6B3A"),
    (10.0, "Moderate", "The 5 models differ moderately.", "#9A6700"),
    (None, "High", "The 5 models differ strongly. Treat this forecast as highly uncertain.", "#A63D40"),
)


def _e(value):
    return html.escape(str(value))


def state_view(state):
    try:
        return STATE_STYLE[state]
    except KeyError:
        raise ValueError(f"unknown traffic state: {state!r}")


def disagreement_level(spread):
    """dict(level, meaning, color) for a seed spread in percentage points: up to 5.0 Low, up to 10.0 Moderate, above High."""
    for limit, level, meaning, color in DISAGREEMENT:
        if limit is None or spread <= limit:
            return {"level": level, "meaning": meaning, "color": color}


def gauge_position(spread):
    """Marker position on the gauge in percent (0 to 100); values outside 0..15 points sit at the ends."""
    return max(0.0, min(float(spread), GAUGE_MAX)) / GAUGE_MAX * 100


def card_html(forecast, placeholder=False):
    """HTML of the forecast card as ONE line without indentation (Streamlit markdown would turn indented HTML into code)."""
    v = state_view(forecast["predicted_state"])
    tag = _e(MOCK_TAG) if placeholder else ""
    pct = f"{forecast['predicted_bot_pct_next_minute']:.2f}"
    small = f"font-size:0.78rem;letter-spacing:0.06em;text-transform:uppercase;color:{MUTED};"
    return "".join([
        f'<div style="border:1px solid {BORDER};border-left:8px solid {v["accent"]};border-radius:12px;padding:18px 20px;'
        f'background:{CARD_BG};box-shadow:0 1px 3px rgba(46,43,40,0.12);">',
        f'<div style="{small}">Forecast (t+1 min) &middot; model status: {_e(forecast["model_status"])}</div>',
        f'<div style="font-size:2.8rem;font-weight:700;line-height:1.15;color:{INK};margin-top:4px;">{pct} %'
        f'<span style="font-size:1rem;font-weight:600;color:{MUTED};">{tag}</span></div>',
        f'<div style="font-size:0.9rem;color:{MUTED};">Predicted bot traffic share for the next minute</div>',
        f'<div style="{small}margin-top:14px;">Estimated traffic state</div>',
        f'<div style="margin-top:4px;"><span style="display:inline-block;background:{v["accent"]};color:#FFFFFF;font-weight:700;'
        f'padding:6px 14px;border-radius:999px;">{_e(v["label"])} ({_e(v["range"])})</span>'
        f'<span style="font-size:1rem;font-weight:600;color:{MUTED};">{tag}</span></div>',
        f'<div style="margin-top:6px;font-size:0.9rem;color:{INK};">{_e(v["sub"])}</div>',
        '</div>',
    ])


def gauge_html(spread):
    """Model Disagreement gauge: three coloured zones (0-5, 5-10, 10-15 points) and a marker at the current spread.
    Text inherits the page colour, so it stays readable on both the cream and the black page."""
    d = disagreement_level(spread)
    zones = ("linear-gradient(to right,#9DB38F 0%,#9DB38F 33.33%,#E0B565 33.33%,#E0B565 66.66%,#C98383 66.66%,#C98383 100%)")
    return "".join([
        f'<div style="font-weight:700;">Model Disagreement: {float(spread):.2f} percentage points</div>',
        f'<div style="margin-top:4px;"><span style="display:inline-block;background:{d["color"]};color:#FFFFFF;font-weight:600;'
        f'padding:2px 12px;border-radius:999px;">{_e(d["level"])} disagreement</span> <span>{_e(d["meaning"])}</span></div>',
        f'<div style="position:relative;height:12px;border-radius:6px;margin:12px 0 4px 0;background:{zones};">'
        f'<div style="position:absolute;left:{gauge_position(spread):.1f}%;top:-4px;width:4px;height:20px;margin-left:-2px;'
        f'border-radius:2px;background:{INK};"></div></div>',
        '<div style="display:flex;justify-content:space-between;font-size:0.72rem;opacity:0.7;">'
        '<span>0</span><span>5</span><span>10</span><span>15+ points</span></div><div style="height:16px;"></div>',
    ])


def seed_series(forecast):
    """The five seed predictions as a labelled Series in seed order (Seed 42 ... Seed 46)."""
    items = list(forecast["seed_predictions"].items())
    try:
        items.sort(key=lambda kv: int(kv[0]))
    except ValueError:
        items.sort(key=lambda kv: str(kv[0]))
    return pd.Series({f"Seed {k}": float(v) for k, v in items}, name="Predicted bot %")


def observed_vs_forecast_frame(window, forecast_pct):
    """Frame for a line chart. x is the minute relative to the newest row (-4 .. 0 observed, 1 = forecast).
    'Observed' covers the 5 input minutes only; 'Forecast' joins the newest observation to the forecast point."""
    n = len(window)
    x = list(range(-(n - 1), 1)) + [1]
    observed = [float(v) for v in window["Bot_Pct"]] + [float("nan")]
    forecast = [float("nan")] * (n - 1) + [observed[n - 1], float(forecast_pct)]
    frame = pd.DataFrame({"Observed bot %": observed, "Forecast bot % (t+1)": forecast,
                          "Medium starts (25%)": 25.0, "High starts (50%)": 50.0}, index=x)
    frame.index.name = "Minute relative to the newest row (t)"
    return frame


def describe_forecast(window, forecast):
    """Plain statements about the numbers (trend, forecast versus the newest minute, disagreement).
    They describe the input and the response. They do not claim to show how the neural network decided."""
    bot = [float(v) for v in window["Bot_Pct"]]
    first, last, change = bot[0], bot[-1], bot[-1] - bot[0]
    word = "rose" if change >= TREND_DELTA else "fell" if change <= -TREND_DELTA else "stayed roughly steady"
    pct = float(forecast["predicted_bot_pct_next_minute"])
    diff = pct - last
    versus = ("the same as" if diff == 0 else f"{abs(diff):.1f} points {'above' if diff > 0 else 'below'}")
    d = disagreement_level(forecast["seed_spread_pct_points"])
    return [f"Over the last 5 minutes the bot share {word} ({first:.1f}% to {last:.1f}%).",
            f"The forecast for the next minute is {pct:.1f}%, which is {versus} the newest minute ({last:.1f}%).",
            f"The 5 models differ by {float(forecast['seed_spread_pct_points']):.2f} points ({d['level'].lower()} disagreement). {d['meaning']}"]


# ---------------------------------------------------------------- Phase 4: traffic analytics for the 5-minute window
# Meanings are from docs/PREPROCESSING.md. The unit of Avg_Duration_Bot and the exact definition of Bot_Pct are still to be
# confirmed by the dataset team, so no value is converted and nothing is derived from them.
FEATURE_INFO = [
    ("Bot_Pct", "Bot share", "Percentage of the minute's flows classified as bot", "%"),
    ("Total_Flows", "Total flows", "Network flows counted in the minute", "flows"),
    ("Fwd_Pkts_Bot", "Forward packets (bot flows)", "Forward packets summed over the bot flows of the minute", "packets"),
    ("Bwd_Pkts_Bot", "Backward packets (bot flows)", "Backward packets summed over the bot flows of the minute", "packets"),
    ("Fwd_Bytes_Bot", "Forward bytes (bot flows)", "Forward bytes summed over the bot flows of the minute", "bytes"),
    ("Bwd_Bytes_Bot", "Backward bytes (bot flows)", "Backward bytes summed over the bot flows of the minute", "bytes"),
    ("Avg_Duration_Bot", "Average duration (bot flows)", "Mean duration of the bot flows of the minute", "unit not confirmed yet"),
]
LABEL = {name: label for name, label, _, _ in FEATURE_INFO}
X_NAME = "Minute relative to the newest row (t)"
CHART_LABEL = {"Fwd_Pkts_Bot": "Forward packets", "Bwd_Pkts_Bot": "Backward packets", "Fwd_Bytes_Bot": "Forward bytes",
               "Bwd_Bytes_Bot": "Backward bytes", "Avg_Duration_Bot": "Average duration"}      # short, so chart legends are not cut off


def observed_state(pct):
    """Low / Medium / High for an OBSERVED bot share, using the project's thresholds (same rule as predict_lstm.state_from_pct)."""
    return "Low" if pct < 25 else ("Medium" if pct < 50 else "High")


def format_value(name, value):
    if name == "Bot_Pct":
        return f"{float(value):.1f} %"
    if name == "Avg_Duration_Bot":
        return f"{float(value):,.1f}"
    return f"{float(value):,.0f}"


def format_delta(name, delta):
    return f"{float(delta):+.1f} pts" if name == "Bot_Pct" else (f"{float(delta):+,.1f}" if name == "Avg_Duration_Bot" else f"{float(delta):+,.0f}")


def analytics_summary(window):
    """Latest / average / minimum / maximum of every feature over the window, one row per feature."""
    rows = {}
    for name, label, _, unit in FEATURE_INFO:
        v = window[name].astype(float)
        rows[f"{label} ({unit})"] = {"Latest": v.iloc[-1], "Average": v.mean(), "Minimum": v.min(), "Maximum": v.max()}
    return pd.DataFrame(rows).T


def series_frame(window, names, thresholds=False):
    """Line-chart frame of the chosen features. x is the minute relative to the newest row (-4 .. 0)."""
    n = len(window)
    frame = pd.DataFrame({CHART_LABEL.get(c, LABEL[c]): [float(v) for v in window[c]] for c in names}, index=list(range(-(n - 1), 1)))
    if thresholds:
        frame["Medium starts (25%)"], frame["High starts (50%)"] = 25.0, 50.0
    frame.index.name = X_NAME
    return frame


def state_table(window):
    """One row per observed minute with the state its bot share falls in. This is an observation, not a model output."""
    n = len(window)
    pct = [float(v) for v in window["Bot_Pct"]]
    table = pd.DataFrame({"Minute": ["t" if i == n - 1 else f"t-{n - 1 - i}" for i in range(n)],
                          "Bot share (%)": pct, "Observed state": [observed_state(p) for p in pct]})
    if "Timestamp" in window.columns:
        table.insert(1, "Timestamp", [str(t) for t in window["Timestamp"]])
    return table


def change_text(name, current, previous):
    """Change from the previous minute as text for a card, or None when it rounds to zero (so no arrow is drawn)."""
    d = float(current) - float(previous)
    if round(d, 1 if name in ("Bot_Pct", "Avg_Duration_Bot") else 0) == 0:
        return None
    return format_delta(name, d)


def analytics_summary_display(window):
    """analytics_summary() with every value formatted as text (thousands separators, units), for showing in a table."""
    nums = analytics_summary(window)
    names = [n for n, *_ in FEATURE_INFO]
    return pd.DataFrame([[format_value(n, v) for v in nums.iloc[i]] for i, n in enumerate(names)],
                        index=nums.index, columns=nums.columns)


def feature_table_markdown():
    """The 7-feature table as a markdown table (it wraps long text instead of cutting it off)."""
    rows = ["| Column name | Shown as | Meaning | Unit |", "|---|---|---|---|"]
    rows += [f"| `{name}` | {label} | {meaning} | {unit} |" for name, label, meaning, unit in FEATURE_INFO]
    return "\n".join(rows)


def seed_caption(forecast):
    """One line with the five seed predictions as numbers (the bar chart is flat when all values are equal or zero)."""
    return " | ".join(f"{k}: {v:.2f}%" for k, v in seed_series(forecast).items())


# One colour per chart series (earthy palette, readable on the cream and the black page). The thresholds use the same
# colours as the amber and red zones of the Model Disagreement gauge.
FOREST, BROWN, AMBER, RED = "#4F8A5B", "#B5651D", "#C9922E", "#B85450"
SERIES_COLOR = {"Bot share": FOREST, "Observed bot %": FOREST, "Forecast bot % (t+1)": BROWN,
                "Medium starts (25%)": AMBER, "High starts (50%)": RED,
                "Total flows": FOREST, "Average duration": FOREST,
                "Forward packets": FOREST, "Backward packets": BROWN, "Forward bytes": FOREST, "Backward bytes": BROWN}


def chart_colors(frame):
    """Colours for st.line_chart(frame, color=...): one per column, in column order."""
    return [SERIES_COLOR[c] for c in frame.columns]

