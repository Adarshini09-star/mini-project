"""Tests for display.py and the Phase 3 wording.  Run from the frontend/ folder:   python -m unittest discover -s tests -v"""
import copy, re, sys, unittest
from html.parser import HTMLParser
from pathlib import Path

FRONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONT)); sys.path.insert(0, str(FRONT / "tests"))
import pandas as pd
import api_client as api
import display as D
import ui_text as T
import validation as V
import test_api_client as TA

VOID = {"br", "hr", "img", "input", "meta", "link"}


class Balanced(HTMLParser):
    """Checks that every opened tag is closed in order."""
    def __init__(self):
        super().__init__(); self.stack, self.ok = [], True
    def handle_starttag(self, tag, attrs):
        if tag not in VOID: self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag: self.ok = False


def balanced(markup):
    p = Balanced(); p.feed(markup); return p.ok and not p.stack


def forecast(pct=34.85, state="Medium", spread=4.1, status="PROVISIONAL"):
    f = copy.deepcopy(api.MOCK_FORECAST_RESPONSE)
    f.update(predicted_bot_pct_next_minute=pct, predicted_state=state, seed_spread_pct_points=spread, model_status=status,
             seed_predictions={"46": 34.5, "42": 33.1, "45": 35.0, "43": 34.5, "44": 37.2})
    return f


def window(bot=(18.0, 19.5, 17.2, 20.1, 18.8)):
    return pd.DataFrame({"Bot_Pct": list(bot)})


class StateAndGauge(unittest.TestCase):
    def test_every_state_has_a_distinct_neutral_style(self):
        self.assertEqual(set(D.STATE_STYLE), set(api.STATES))
        self.assertEqual(len({v["accent"] for v in D.STATE_STYLE.values()}), 3)
        text = " ".join(" ".join(v.values()).lower() for v in D.STATE_STYLE.values())
        for word in ("attack", "threat", "safe"):
            self.assertNotIn(word, text)

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            D.state_view("Critical")

    def test_disagreement_boundaries_follow_the_handoff(self):
        for spread, level in [(0, "Low"), (5.0, "Low"), (5.01, "Moderate"), (10.0, "Moderate"), (10.01, "High"), (40, "High")]:
            with self.subTest(spread=spread):
                self.assertEqual(D.disagreement_level(spread)["level"], level)

    def test_gauge_position_is_clamped(self):
        self.assertEqual([D.gauge_position(v) for v in (-3, 0, 7.5, 15, 99)], [0.0, 0.0, 50.0, 100.0, 100.0])


class CardAndGauge(unittest.TestCase):
    def test_card_shows_the_backend_values(self):
        h = D.card_html(forecast())
        for text in ("34.85 %", "MEDIUM", "25% to below 50% bot", "Forecast (t+1 min)", "model status: PROVISIONAL",
                     "Predicted bot traffic share for the next minute", "Estimated traffic state"):
            self.assertIn(text, h)
        self.assertNotIn("[MOCK]", h)

    def test_percentage_is_shown_with_two_decimals(self):
        for pct, text in [(34.8549, "34.85 %"), (34.8551, "34.86 %"), (0.0, "0.00 %"), (100.0, "100.00 %"), (7, "7.00 %")]:
            with self.subTest(pct=pct):
                self.assertIn(text, D.card_html(forecast(pct=pct)))

    def test_state_comes_from_the_backend_not_from_the_percentage(self):
        h = D.card_html(forecast(pct=60.0, state="Low"))          # inconsistent on purpose: the card must show what it was told
        self.assertIn("LOW", h); self.assertNotIn("HIGH", h)

    def test_placeholder_tag_appears_next_to_number_and_badge(self):
        h = D.card_html(forecast(pct=0.0, state="Low", status="MOCK"), placeholder=True)
        self.assertEqual(h.count("[MOCK]"), 2)
        self.assertIn("0.00 %<span", h)

    def test_markup_is_one_line_balanced_and_escaped(self):
        for state in api.STATES:
            for markup in (D.card_html(forecast(state=state)), D.gauge_html(7.3)):
                self.assertNotIn("\n", markup)
                self.assertFalse(markup.startswith(" "))
                self.assertTrue(balanced(markup), markup)
        evil = forecast(); evil["model_status"] = "<script>x</script>"
        self.assertNotIn("<script>", D.card_html(evil))

    def test_gauge_text(self):
        h = D.gauge_html(4.1)
        self.assertIn("Model Disagreement: 4.10 percentage points", h)
        self.assertIn("Low disagreement", h)
        self.assertIn("High disagreement", D.gauge_html(12))
        self.assertIn("left:100.0%", D.gauge_html(99))

    def test_gauge_text_follows_the_page_colour(self):          # the page can be cream or black (theme_switch.py)
        g = D.gauge_html(7.0)
        self.assertNotIn("color:#2E2B28", g)                    # no fixed dark text that would vanish on a black page
        self.assertNotIn("color:#6B5D4F", g)
        self.assertIn("Moderate disagreement", g)


class ChartsAndText(unittest.TestCase):
    def test_seed_series_is_in_seed_order(self):
        s = D.seed_series(forecast())
        self.assertEqual(list(s.index), ["Seed 42", "Seed 43", "Seed 44", "Seed 45", "Seed 46"])
        self.assertEqual(s["Seed 44"], 37.2)

    def test_observed_vs_forecast_frame(self):
        fr = D.observed_vs_forecast_frame(window(), 30.0)
        self.assertEqual(list(fr.index), [-4, -3, -2, -1, 0, 1])
        self.assertEqual(fr["Observed bot %"].tolist()[:5], [18.0, 19.5, 17.2, 20.1, 18.8])
        self.assertTrue(pd.isna(fr["Observed bot %"].iloc[-1]))
        fc = fr["Forecast bot % (t+1)"]
        self.assertTrue(fc.iloc[:4].isna().all())
        self.assertEqual((fc.iloc[4], fc.iloc[5]), (18.8, 30.0))                  # joins the newest observation to the forecast
        self.assertTrue((fr["Medium starts (25%)"] == 25).all() and (fr["High starts (50%)"] == 50).all())

    def test_description_rising_falling_steady(self):
        up = D.describe_forecast(window((10, 12, 14, 16, 20)), forecast(pct=26.0))
        self.assertIn("rose (10.0% to 20.0%)", up[0]); self.assertIn("6.0 points above the newest minute (20.0%)", up[1])
        down = D.describe_forecast(window((40, 35, 30, 28, 25)), forecast(pct=20.0))
        self.assertIn("fell", down[0]); self.assertIn("5.0 points below", down[1])
        flat = D.describe_forecast(window((20, 21, 19, 20, 20)), forecast(pct=20.0))
        self.assertIn("roughly steady", flat[0]); self.assertIn("the same as the newest minute", flat[1])

    def test_description_mentions_disagreement(self):
        self.assertIn("highly uncertain", D.describe_forecast(window(), forecast(spread=12.0))[2])
        self.assertIn("agree closely", D.describe_forecast(window(), forecast(spread=1.0))[2])


def full_window(**over):
    d = {"Bot_Pct": [18.0, 19.5, 17.2, 20.1, 18.8], "Total_Flows": [1800, 1850, 1790, 1900, 1830],
         "Fwd_Pkts_Bot": [1050, 1100, 1020, 1150, 1080], "Bwd_Pkts_Bot": [820, 860, 800, 890, 840],
         "Fwd_Bytes_Bot": [63000, 66000, 61000, 68000, 65000], "Bwd_Bytes_Bot": [28000, 30000, 27500, 31000, 29500],
         "Avg_Duration_Bot": [22000, 23000, 21500, 24000, 22500]}
    d.update(over)
    df = pd.DataFrame(d).astype(float)
    df.insert(0, "Timestamp", pd.date_range("2018-02-03 09:00", periods=5, freq="min"))
    return df


class Analytics(unittest.TestCase):
    def test_observed_state_matches_the_repos_own_rule(self):
        import random
        try:
            import predict_lstm
        except Exception:
            self.skipTest("predict_lstm.py not importable here")
        values = [0, 24.999, 25, 25.0001, 49.999, 50, 50.0001, 100] + [random.Random(7).uniform(0, 100) for _ in range(500)]
        for v in values:
            self.assertEqual(D.observed_state(v), predict_lstm.state_from_pct(v), v)

    def test_every_feature_has_info_and_matches_the_api_features(self):
        self.assertEqual([n for n, *_ in D.FEATURE_INFO], api.FEATURES)
        for name, label, meaning, unit in D.FEATURE_INFO:
            self.assertTrue(label and meaning and unit)
        self.assertIn("not confirmed", dict((n, u) for n, _, _, u in D.FEATURE_INFO)["Avg_Duration_Bot"])

    def test_summary_numbers(self):
        s = D.analytics_summary(full_window())
        row = s.loc["Total flows (flows)"]
        self.assertEqual((row["Latest"], row["Average"], row["Minimum"], row["Maximum"]), (1830.0, 1834.0, 1790.0, 1900.0))
        self.assertEqual(len(s), 7)
        self.assertIn("Average duration (bot flows) (unit not confirmed yet)", s.index)

    def test_series_frames(self):
        f = D.series_frame(full_window(), ["Fwd_Pkts_Bot", "Bwd_Pkts_Bot"])
        self.assertEqual(list(f.index), [-4, -3, -2, -1, 0])
        self.assertEqual(list(f.columns), ["Forward packets", "Backward packets"])               # short, so legends are not cut off
        self.assertEqual(f["Backward packets"].tolist(), [820, 860, 800, 890, 840])
        for names in (["Fwd_Pkts_Bot", "Bwd_Pkts_Bot"], ["Fwd_Bytes_Bot", "Bwd_Bytes_Bot"], ["Avg_Duration_Bot"], ["Total_Flows"], ["Bot_Pct"]):
            self.assertTrue(all(len(c) <= 20 for c in D.series_frame(full_window(), names).columns), names)
        t = D.series_frame(full_window(), ["Bot_Pct"], thresholds=True)
        self.assertTrue((t["Medium starts (25%)"] == 25).all() and (t["High starts (50%)"] == 50).all())

    def test_state_table_and_numeric_text_cells(self):
        w = full_window(Bot_Pct=[10.0, 24.9, 25.0, 49.9, 50.0])
        t = D.state_table(w)
        self.assertEqual(t["Observed state"].tolist(), ["Low", "Low", "Medium", "Medium", "High"])
        self.assertEqual(t["Minute"].tolist(), ["t-4", "t-3", "t-2", "t-1", "t"])
        self.assertEqual(t["Timestamp"].iloc[0], "2018-02-03 09:00:00")
        self.assertNotIn("Timestamp", D.state_table(w.drop(columns="Timestamp")).columns)
        text = full_window().astype(object); text.loc[4, "Total_Flows"] = "1830"      # numeric text is accepted by the validator
        self.assertEqual(D.analytics_summary(text).loc["Total flows (flows)", "Latest"], 1830.0)

    def test_every_chart_series_has_a_colour(self):
        import re
        w = full_window()
        frames = [D.observed_vs_forecast_frame(w, 30.0), D.series_frame(w, ["Bot_Pct"], thresholds=True)]
        frames += [D.series_frame(w, n) for n in (["Fwd_Pkts_Bot", "Bwd_Pkts_Bot"], ["Avg_Duration_Bot"], ["Total_Flows"], ["Fwd_Bytes_Bot", "Bwd_Bytes_Bot"])]
        for fr in frames:
            colours = D.chart_colors(fr)
            self.assertEqual(len(colours), len(fr.columns))
            self.assertTrue(all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in colours), colours)
            self.assertEqual(len(set(colours)), len(colours), fr.columns.tolist())      # series in one chart are told apart
        self.assertTrue(all(len(c) <= 20 for c in frames[0].columns))                   # legends are not cut off

    def test_cards_show_no_arrow_when_nothing_changed(self):
        self.assertIsNone(D.change_text("Total_Flows", 400, 400))
        self.assertIsNone(D.change_text("Bot_Pct", 18.04, 18.0))                    # rounds to +0.0 pts
        self.assertIsNone(D.change_text("Avg_Duration_Bot", 5000.0, 5000.04))
        self.assertEqual(D.change_text("Bot_Pct", 20.1, 18.0), "+2.1 pts")
        self.assertEqual(D.change_text("Total_Flows", 1800, 1850), "-50")

    def test_summary_table_text_matches_the_cards(self):
        s = D.analytics_summary_display(full_window())
        self.assertEqual(list(s.columns), ["Latest", "Average", "Minimum", "Maximum"])
        self.assertEqual(s.loc["Total flows (flows)"].tolist(), ["1,830", "1,834", "1,790", "1,900"])
        self.assertEqual(s.loc["Forward bytes (bot flows) (bytes)", "Latest"], "65,000")
        self.assertEqual(s.loc["Bot share (%)", "Latest"], "18.8 %")
        self.assertEqual(len(s), 7)

    def test_feature_table_markdown(self):
        md = D.feature_table_markdown().split("\n")
        self.assertEqual(len(md), 2 + 7)
        self.assertTrue(all(line.startswith("|") and line.endswith("|") for line in md))
        self.assertIn("unit not confirmed yet", md[-1])
        self.assertIn("`Bot_Pct`", md[2])

    def test_seed_caption(self):
        self.assertEqual(D.seed_caption(forecast()), "Seed 42: 33.10% | Seed 43: 34.50% | Seed 44: 37.20% | Seed 45: 35.00% | Seed 46: 34.50%")

    def test_formatting(self):
        self.assertEqual(D.format_value("Bot_Pct", 18.84), "18.8 %")
        self.assertEqual(D.format_value("Total_Flows", 1830), "1,830")
        self.assertEqual(D.format_value("Avg_Duration_Bot", 22500), "22,500.0")
        self.assertEqual(D.format_delta("Bot_Pct", -1.3), "-1.3 pts")
        self.assertEqual(D.format_delta("Total_Flows", 70), "+70")

    def test_about_text_is_complete_and_careful(self):
        text = " ".join(h + b for h, b in T.ABOUT_SECTIONS).lower()
        for needle in ("not real-time", "42 to 46", "not proof that traffic is safe", "102 target windows", "never loads the model"):
            self.assertIn(needle, text)
        self.assertEqual(len(T.ABOUT_SECTIONS), 4)
        self.assertIn("still to be confirmed", T.ABOUT_DOC_NOTE)


class WordingRules(unittest.TestCase):
    def test_forbidden_words_are_absent(self):
        for name in ("display.py", "app.py", "ui_text.py"):
            text = (FRONT / name).read_text(encoding="utf-8").lower()
            for word in ("confidence", "accuracy", "certainty", "shap"):
                self.assertIsNone(re.search(rf"\b{word}\b", text), f"{word!r} found in {name}")

    def test_state_notices(self):
        self.assertEqual(set(T.STATE_NOTICE), set(api.STATES))
        self.assertIn("Low-state recall is about 0%", T.STATE_NOTICE["Low"])
        self.assertIn("does not show that traffic is safe", T.STATE_NOTICE["Medium"])
        self.assertIn("not confirmation of an attack", T.STATE_NOTICE["High"])

    def test_mandatory_limitations_and_footer(self):
        self.assertEqual(len(T.LIMITATIONS), 4)
        self.assertIn("CSE-CIC-IDS2018", T.FOOTER)
        self.assertIn("Offline", T.FOOTER)

    @unittest.skipUnless(TA.DOC, "needs docs/API_CONTRACT.md")
    def test_contract_example_response_renders(self):
        f = TA.SUCCESS_DOC
        self.assertTrue(balanced(D.card_html(f)) and balanced(D.gauge_html(f["seed_spread_pct_points"])))
        self.assertEqual(len(D.seed_series(f)), 5)
        self.assertEqual(len(D.describe_forecast(window(), f)), 3)
        self.assertIn(f"{f['predicted_bot_pct_next_minute']:.2f} %", D.card_html(f))


if __name__ == "__main__":
    unittest.main()
