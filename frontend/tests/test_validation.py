"""Tests for validation.py.  Run from the frontend/ folder:   python -m unittest discover -s tests -v

The key test compares the client-side checks with the REAL predict_lstm.validate_window() on hundreds of random
mistakes: both must give the same first error code. Tests that need ../predict_lstm.py or ../docs/ are skipped without them.
"""
import json, random, re, sys, threading, unittest
from pathlib import Path

FRONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONT)); sys.path.insert(0, str(FRONT / "tests"))
import numpy as np
import pandas as pd
import api_client as api
import ui_text as T
import validation as V
import test_api_client as TA                       # re-uses its stand-in backend and the contract example

REAL = TA.VALIDATE
EXAMPLE = pd.DataFrame(TA.EXAMPLE_REQUEST["window"]).astype({c: float for c in V.FEATURES}) if TA.DOC else None
CASES = 400


def real_code(df):
    try:
        TA.VALIDATE(df)
        return None
    except TA.VALIDATION_ERROR as e:
        return e.code


def first_code(df):
    issues = V.validate_window(df)
    return issues[0].code if issues else None


@unittest.skipUnless(REAL and EXAMPLE is not None, "needs predict_lstm.py and docs/API_CONTRACT.md")
class AgreesWithRealValidator(unittest.TestCase):
    def test_example_is_valid_for_both(self):
        self.assertEqual((first_code(EXAMPLE), real_code(EXAMPLE)), (None, None))

    def test_random_mistakes_give_the_same_first_error(self):
        rng = random.Random(2018)
        seen = set()
        for i in range(CASES):
            df = EXAMPLE.copy()
            for _ in range(rng.randint(1, 3)):
                kind = rng.choice(["nan", "neg", "inf", "big_bot", "bad_ts", "gap", "drop_row", "drop_col", "drop_ts",
                                   "dup_row", "reverse", "none"])
                r, c = rng.randrange(len(df)) if len(df) else 0, rng.choice(V.FEATURES)
                if kind == "nan" and len(df): df.loc[df.index[r], c] = np.nan
                elif kind == "neg" and len(df): df.loc[df.index[r], c] = -rng.random() * 10
                elif kind == "inf" and len(df): df.loc[df.index[r], c] = float("inf")
                elif kind == "big_bot" and len(df): df.loc[df.index[r], "Bot_Pct"] = 100 + rng.random() * 50
                elif kind == "bad_ts" and len(df) and "Timestamp" in df: df.loc[df.index[r], "Timestamp"] = "oops"
                elif kind == "gap" and len(df) and "Timestamp" in df: df.loc[df.index[r], "Timestamp"] = "2018-02-03T10:30:00"
                elif kind == "drop_row" and len(df): df = df.drop(df.index[r])
                elif kind == "drop_col" and c in df: df = df.drop(columns=[c])
                elif kind == "drop_ts" and "Timestamp" in df: df = df.drop(columns=["Timestamp"])
                elif kind == "dup_row" and len(df): df = pd.concat([df, df.iloc[[r]]])
                elif kind == "reverse": df = df.iloc[::-1]
            df = df.reset_index(drop=True)
            expected, got = real_code(df), first_code(df)
            self.assertEqual(got, expected, f"case {i}: client={got} real={expected}\n{df}")
            seen.add(expected)
        # the random test must actually have exercised every code
        self.assertTrue({"MISSING_FEATURES", "BAD_TIMESTAMP", "NOT_CONSECUTIVE", "BAD_SHAPE", "NAN_OR_INF",
                         "NEGATIVE_VALUE", "BOT_PCT_RANGE", None} <= seen, seen)

    def test_validation_does_not_change_the_table(self):
        df = EXAMPLE.copy(); df.loc[2, "Total_Flows"] = -5
        before = df.copy(deep=True)
        V.validate_window(df)
        pd.testing.assert_frame_equal(df, before)


class HandCases(unittest.TestCase):
    def good(self):
        return V.table_to_window(V.presets()["Typical traffic (example)"], V.DEFAULT_START)[0]

    def test_all_presets_are_valid(self):
        for name, table in V.presets().items():
            with self.subTest(name=name):
                window, issues = V.table_to_window(table, V.DEFAULT_START)
                self.assertEqual(issues, [])
                self.assertEqual(len(window), 5)
                self.assertEqual(list(window.columns), ["Timestamp"] + V.FEATURES)
                self.assertEqual(list(window["Timestamp"].diff().dropna().dt.total_seconds()), [60.0] * 4)

    def test_text_in_a_number_cell(self):
        w = self.good().astype(object); w.loc[1, "Total_Flows"] = "abc"
        self.assertEqual([i.code for i in V.validate_window(w)], ["NOT_NUMERIC"])

    def test_numeric_text_is_accepted(self):
        w = self.good().astype(object); w.loc[1, "Total_Flows"] = "1500"
        self.assertEqual(V.validate_window(w), [])

    def test_empty_cell(self):
        t = V.presets()["Quiet traffic (example)"].copy(); t.loc[3, "Bwd_Pkts_Bot"] = np.nan
        self.assertEqual([i.code for i in V.table_to_window(t, V.DEFAULT_START)[1]], ["NAN_OR_INF"])

    def test_bad_start_time(self):
        window, issues = V.table_to_window(V.presets()["Quiet traffic (example)"], "tomorrow-ish")
        self.assertIsNone(window)
        self.assertEqual(issues[0].code, "BAD_TIMESTAMP")

    def test_several_problems_are_all_listed(self):
        t = V.presets()["Quiet traffic (example)"].copy(); t.loc[0, "Total_Flows"] = -1; t.loc[1, "Bot_Pct"] = 120
        codes = [i.code for i in V.table_to_window(t, V.DEFAULT_START)[1]]
        self.assertEqual(codes, ["NEGATIVE_VALUE", "BOT_PCT_RANGE"])

    def test_table_is_not_changed(self):
        t = V.presets()["Busy traffic (example)"]; before = t.copy(deep=True)
        V.table_to_window(t, V.DEFAULT_START)
        pd.testing.assert_frame_equal(t, before)

    def test_every_code_used_in_validation_has_a_message(self):
        text = (FRONT / "validation.py").read_text(encoding="utf-8")
        used = set(re.findall(r'(?:Issue|InputFileError)\(\s*"([A-Z_]+)"', text))
        self.assertTrue({"MISSING_FEATURES", "NOT_NUMERIC", "BAD_CSV", "FILE_TOO_LARGE"} <= used)
        self.assertEqual([c for c in sorted(used) if c not in T.ERROR_MESSAGES], [])

    def test_forbidden_wording_is_absent(self):
        for name in ("validation.py", "app.py"):
            text = (FRONT / name).read_text(encoding="utf-8").lower()
            for word in ("confidence", "accuracy", "certainty", "shap"):
                self.assertIsNone(re.search(rf"\b{word}\b", text), f"{word!r} found in {name}")


class CsvReading(unittest.TestCase):
    HEADER = "Timestamp," + ",".join(V.FEATURES)

    def rows(self, n, start_minute=0):
        return [f"2018-02-03 09:{start_minute + i:02d}:00,{10 + i},100,50,40,3000,2000,900" for i in range(n)]

    def csv(self, rows, header=None):
        return ((header or self.HEADER) + "\n" + "\n".join(rows) + "\n").encode()

    def test_last_five_rows_are_used(self):
        w, info = V.read_csv_window(self.csv(self.rows(8)))
        self.assertEqual((len(w), info["total_rows"], info["used_rows"]), (5, 8, 5))
        self.assertEqual(w["Bot_Pct"].tolist(), [13, 14, 15, 16, 17])
        self.assertEqual(V.validate_window(w), [])

    def test_header_spaces_bom_and_extra_columns(self):
        header = "\ufeff Timestamp , Bot_Pct , Total_Flows,Fwd_Pkts_Bot,Bwd_Pkts_Bot,Fwd_Bytes_Bot,Bwd_Bytes_Bot,Avg_Duration_Bot,Label"
        rows = [r + ",Benign" for r in self.rows(5)]
        w, info = V.read_csv_window(self.csv(rows, header))
        self.assertEqual(list(w.columns), ["Timestamp"] + V.FEATURES)
        self.assertEqual(info["ignored_columns"], ["Label"])
        self.assertEqual(V.validate_window(w), [])

    def test_without_timestamp_column(self):
        rows = [r.split(",", 1)[1] for r in self.rows(5)]
        w, info = V.read_csv_window(self.csv(rows, ",".join(V.FEATURES)))
        self.assertFalse(info["has_timestamp"])
        self.assertEqual(V.validate_window(w), [])

    def test_too_few_rows_missing_columns_and_gaps_are_reported(self):
        w, _ = V.read_csv_window(self.csv(self.rows(3)))
        self.assertEqual([i.code for i in V.validate_window(w)], ["BAD_SHAPE"])
        w, _ = V.read_csv_window(self.csv([r.rsplit(",", 1)[0] for r in self.rows(5)], self.HEADER.rsplit(",", 1)[0]))
        self.assertEqual([i.code for i in V.validate_window(w)], ["MISSING_FEATURES"])
        rows = self.rows(5); rows[2] = rows[2].replace("09:02", "09:07")
        w, _ = V.read_csv_window(self.csv(rows))
        self.assertEqual([i.code for i in V.validate_window(w)], ["NOT_CONSECUTIVE"])

    def test_unreadable_files(self):
        for data in (b"", b"\xff\xfe\x00\x80\x81binary", b"   \n  \n"):
            with self.subTest(data=data[:6]):
                with self.assertRaises(V.InputFileError) as cm:
                    V.read_csv_window(data)
                self.assertEqual(cm.exception.code, "BAD_CSV")
        with self.assertRaises(V.InputFileError) as cm:
            V.read_csv_window(self.csv(self.rows(5)), max_bytes=50)
        self.assertEqual(cm.exception.code, "FILE_TOO_LARGE")


@unittest.skipUnless(REAL and TA.DOC, "needs predict_lstm.py and docs/API_CONTRACT.md")
class EndToEndWithStandInBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TA.QuietServer(("127.0.0.1", 0), TA.Stub)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()

    def setUp(self):
        TA.Stub.mode, TA.Stub.delay = "normal", 0.0

    def test_presets_pass_client_checks_and_the_real_validator(self):
        for name, table in V.presets().items():
            with self.subTest(name=name):
                window, issues = V.table_to_window(table, V.DEFAULT_START)
                self.assertEqual(issues, [])
                self.assertEqual(api.request_forecast(window, self.url), TA.SUCCESS_DOC)

    def test_csv_round_trip(self):
        data = EXAMPLE.to_csv(index=False).encode()
        window, _ = V.read_csv_window(data)
        self.assertEqual(V.validate_window(window), [])
        self.assertEqual(api.request_forecast(window, self.url), TA.SUCCESS_DOC)

    def test_a_window_rejected_by_the_client_is_also_rejected_by_the_backend(self):
        bad = EXAMPLE.copy(); bad.loc[3, "Bot_Pct"] = 140
        self.assertEqual(V.validate_window(bad)[0].code, "BOT_PCT_RANGE")
        with self.assertRaises(api.ApiError) as cm:
            api.request_forecast(bad, self.url)
        self.assertEqual(cm.exception.code, "BOT_PCT_RANGE")


if __name__ == "__main__":
    unittest.main()
