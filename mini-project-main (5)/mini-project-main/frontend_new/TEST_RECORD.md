# Frontend Test Record

**Project:** SIH26153, Bot Traffic Forecast Dashboard (Member 4)
**Prepared:** 21 November 2026 (automated results). The browser checks in section 4 are filled in by Member 4.
**What was tested:** the `frontend/` folder (Streamlit dashboard) against `docs/API_CONTRACT.md`, `docs/FRONTEND_HANDOFF.md` and the repo's own `predict_lstm.py` validator.

## 1. Summary

| Layer | What it proves | Status |
|---|---|---|
| Unit tests (93) | The API client, input checks, CSV reading, display logic and wording rules behave as specified | All pass |
| Page-flow check (18 scenarios) | What the page shows in each situation, and that it does not crash | All pass |
| Browser checklist (section 4) | How the page looks and feels, navigation, responsive layout | **To be completed by Member 4** |
| Backend integration (section 5) | The dashboard works with Member 3's real backend and the real model | **Blocked: no backend code is in the repo yet** |

**Important limit:** until a real backend exists, every "API call" in these tests goes to a *stand-in backend* that uses the repo's real `validate_window()` and returns the contract's example response. So the tests prove the dashboard follows the contract. They do not yet prove a real LSTM forecast reaches the screen. The numbers returned by the stand-in (for example 19.12 %) are the contract's example, not model output.

## 2. The 12 items from the project brief

Legend: ✅ proven by automated tests, 🧪 needs the manual browser check, ⏳ needs the real backend.

| # | Item | Evidence | Status |
|---|---|---|---|
| 1 | Dashboard renders correctly | Phase 1 and 2 screens were seen in browser screenshots. Phase 3 and 4 screens (forecast card, gauge, charts, analytics, About) have not been seen yet. | 🧪 M1, M6, M13, M14 |
| 2 | Navigation works | The content of all three tabs is produced correctly (scenarios 11 to 13). Clicking the tabs is not automated. | ✅ content, 🧪 M2 |
| 3 | Charts display actual data | The data behind every chart equals the input values (tests in `test_display.py`, scenario 11). How the charts look is not automated. | ✅ data, 🧪 M13 |
| 4 | CSV upload validation works | 20 validation tests, including 400 random mistakes where the client and the real validator give the same first error. A plain-text file was rejected in the browser. | ✅ |
| 5 | API calls reach the backend | Real HTTP calls reach the stand-in backend (19 tests). The real backend does not exist yet. | ✅ stand-in, ⏳ real |
| 6 | Loading indicators appear | The "Contacting the backend..." and "Waiting for the forecast..." spinners are shown (scenario 14). On a fast local call they may flash by. | ✅ |
| 7 | API errors are handled | All 7 validator codes plus BAD_REQUEST, HTTP 500 (with and without a body), malformed 200 replies, timeout and unreachable backend give a clear message and no card (tests, scenarios 5 and 6). "Cannot reach the backend" was seen in the browser. | ✅ |
| 8 | Forecast percentage displays correctly | Shown with two decimals exactly as the backend sent it (card tests). Matching the real model's value needs the real backend. | ✅ format, ⏳ value |
| 9 | Traffic state is mapped correctly | The card always shows the backend's `predicted_state` and never recomputes it. The observed-state rule on the Analytics tab matches `predict_lstm.state_from_pct` on the boundaries (25, 50) and 500 random values. | ✅ |
| 10 | Model warnings are visible | Every warning in a response is shown in its own box (scenario 14), and the low-recall reminder is always shown. | ✅ |
| 11 | Responsive layouts | Not automated. | 🧪 M15 |
| 12 | Mock data is never confused with real forecasts | In Demo mode and MOCK mode a red banner appears, `[MOCK]` is shown next to the number and the badge, and explanations are hidden (scenarios 1 and 4). The demo values equal the contract's mock response exactly. | ✅ |

## 3. Automated tests

Run from the `frontend/` folder.

```
python -m unittest discover -s tests -v
python tests/app_flow_check.py
```

| File | Tests | What it covers |
|---|---|---|
| `tests/test_api_client.py` | 19 | Requests and responses against the contract example and the real validator, every error code, timeout, unreachable backend, bad addresses, Demo mode, wording rules |
| `tests/test_validation.py` | 20 | Input checks agree with the real validator, table and CSV reading, bad files, end to end through the stand-in backend |
| `tests/test_display.py` | 31 | Forecast card, state styles, disagreement gauge (including readable text on a black page), charts, explanations, analytics numbers, the About text, wording rules |
| `tests/test_backend_check.py` | 10 | The backend integration script itself |
| `tests/test_hero_banner.py` | 9 | The banner: canvas and config, script tag safe, reduced motion, title drawn as real measured text, no digits behind the title or on the frame, faint sparse texture, drawn in an iframe |
| `tests/test_theme_switch.py` | 4 | The cream / black switch (your tests, unchanged) |
| `tests/app_flow_check.py` | 18 scenarios | Demo mode labelling, stand-in backend result, stale-result notice, MOCK mode, server error, unreachable backend, invalid input, CSV flow, analytics, About, loading indicators, all warnings shown, banner drawn once, theme switch written once, an earlier forecast marked out of date when Demo mode or the backend address changes, every chart drawn with one distinct colour per series |

**Results on 21 November 2026** (Python 3.12.3, pandas 3.0.6, numpy 2.5.4): all 93 unit tests pass and all 18 page scenarios pass, run on the merged `frontend_new` folder inside the repo layout (with `docs/` and `predict_lstm.py`).
**Results on Member 4's own computer** (Python 3.11, Streamlit 1.67.0, pandas 3.0.3): the 19 Phase 1 tests passed. Please run both commands again and write the numbers here: unit tests ____ run (expected 93), ____ passed; page scenarios ____ of 18.

What these tests cannot show: colours, spacing, how charts and cards look, and how the page behaves on a phone.

## 4. Manual browser checklist (Member 4 to fill in)

Start the app with `python -m streamlit run app.py` from the `frontend/` folder. Turn **Demo mode** on unless a step says otherwise. "Seen" means a screenshot was already reviewed.

| ID | Steps | Expected | Seen so far | Result | Notes |
|---|---|---|---|---|---|
| M1 | Open the page | Cream background, sand sidebar, yellow PROVISIONAL banner, three tabs: Forecast, Traffic Analytics, About the Model | Seen (cream and black) | | |
| M2 | Click each tab | Each tab shows its own content | Seen on black: all three tabs opened | | |
| M3 | Click **Check backend connection** | Red DEMO MODE banner; "Demo (none)", "mock", "MOCK" | Seen (cream and black) | | |
| M4 | Pick each of the three presets | "Input looks valid" and a 5-row table each time | Seen (Quiet, Typical) | | |
| M5 | Type a negative number in Total_Flows, then 130 in Bot_Pct, then clear a cell, then type `tomorrow` as the time label | A red message each time, and **Get forecast** is greyed out | Seen: the bad time label `tomorrow` gives a red message. Negative value, 130 and a blank cell not yet seen. | | |
| M6 | Click **Get forecast** | Forecast card with `0.00 % [MOCK]` and a LOW badge with `[MOCK]`; gauge marker at the far left; 5 bars; line chart; two mock warnings plus the low-recall reminder; "Not shown for placeholder values" | Seen in Demo mode on black and on cream: card with [MOCK] tags, gauge, advisories, seed numbers, observed-and-forecast chart. | | |
| M7 | Upload a CSV with Timestamp plus the 7 features and at least 5 rows one minute apart | "Input looks valid", "using the last 5" | Seen: a CSV was read (5 rows) and shown as valid. | | |
| M8 | Upload a text file renamed to `.csv` | "could not be read as a CSV table" with the file's column names | Seen: a plain-text file is rejected with the new message and **Get forecast** is greyed out. | | |
| M9 | Upload CSVs with a gap in the times, fewer than 5 rows, and a missing column | The matching message each time | | | |
| M10 | Click **Get forecast** and **Check backend connection** | A spinner shows briefly | Seen: "Waiting for the forecast..." | | |
| M11 | Turn Demo mode off, click both buttons | "Cannot reach the backend..." and no forecast card | Seen (cream and black) | | |
| M12 | Get a forecast, then change a number | Blue notice "made from earlier input values" | Seen (cream and black) | | |
| M13 | Open Traffic Analytics with the "Busy traffic" preset | Bot share 56.0 %, state High, total flows 3,000; 5 charts; observed-state table; summary table | Seen on cream and black with the Quiet and Typical presets. Busy preset not yet. | | |
| M14 | Open About the Model | Four sections, the 7-feature table, limitations | Seen on black | | |
| M15 | Make the browser window narrow (about 600 px), then about 800 px (press F12, then Ctrl+Shift+M for device view) | Columns stack, tables scroll inside their own area, text stays readable, the page itself does not scroll sideways | | | |
| M16 | Read all text on every tab | Nothing says real-time detection, attack detected, or safe. The Low and Medium notices are visible. | | | |
| M17 | Look at the top of the page | A dark banner with BOT TRAFFIC FORECAST in crisp ivory serif capitals inside a thin double frame, a faint sparse texture of green 0s and 1s around it, and no digits behind the letters. Resize the window: the title stays readable and drops to two lines when narrow. It never shows forecast values. | Earlier digit-letter banners seen on cream and black; this one not yet seen | | |
| M18 | Switch **Black background** on and off in the sidebar, then open all three tabs and run a forecast in each colour | The page changes between cream and black; the forecast card, gauge text, charts and tables stay readable in both. (The switch reloads the page, so typed table values reset.) | Seen on black for all three tabs. Gauge text readable on black. | | |

## 5. Backend integration (blocked until Member 3's backend exists)

There is no `api.py` or backend code in the repo yet, so this section cannot be completed. When Member 3 delivers it:

1. Member 3 tells you how to start the backend and its address.
2. Run `python tests/backend_check.py --url http://ADDRESS`. Expected: every line PASS and "ALL CHECKS PASSED". A WARN about MOCK mode means the model is not loaded, and this is **not** a real integration pass.
3. Unzip `phase4_lstm_REGEN_v1_20261101_0503.zip`, then run `python tests/backend_check.py --url http://ADDRESS --compare PATH_TO_UNZIPPED_FOLDER`. This needs TensorFlow. Expected: "PASS backend equals model code for the same window".
4. Start the dashboard with Demo mode off, click **Check backend connection** and **Get forecast** with each preset, and confirm the card shows the same percentage and state that the check printed.

| Date | Backend commit or branch | Command | Result |
|---|---|---|---|
| | | | |

## 6. Known limitations and open items

- The look of the page is not verified by automated tests (section 4).
- No real backend yet, so a real model forecast has never been displayed (section 5).
- The unit of `Avg_Duration_Bot` and the exact definition of `Bot_Pct` are unconfirmed (open questions to Member 1 in `docs/PREPROCESSING.md`). The duration is labelled "unit not confirmed yet", and no bot-flow count is shown.
- The explanations are descriptive statements about the input and the response. They do not show how the neural network decided. SHAP is not used, following `docs/EXPLAINABILITY.md`.
- The traffic state is worded neutrally ("High bot share forecast") and not "High Attack Threat" as in the hand-off table, because the system forecasts bot share and does not detect attacks.
- Cosmetic: for a single flat line, the Average duration chart can show a wider time axis (for example -7 to 0) than its data (-4 to 0). The data itself is correct. The chart library chooses the axis range.
- The validation tests use the repo's `predict_lstm.py`. If that validator changes, these tests must be updated.

## 6a. Changes made after the first browser check

Screenshots of the page in Demo mode and without it, on cream and black, showed these small problems. They are fixed and covered by tests:

- A card showed an up arrow ("↑ +0") when a value had not changed. No arrow is shown now.
- Chart legends were cut off ("Backward packets (bot fl..."). The legend names are shorter.
- The summary table showed `10000` while the cards showed `10,000`. Both use the same format now.
- The 7-feature table on the About tab cut off its last column and showed a row-number column. It is now a wrapped table.
- An error from an earlier request stayed on screen after switching Demo mode on. A forecast is now marked as out of date when the input, Demo mode or the backend address changes.
- The legend of the observed-and-forecast chart was cut off ("Observed bot % (input v..."). It is shorter now.
- Chart lines used default blue, pink and red, so an observed line could be mistaken for a threshold. Each series now has its own earthy colour, and the 25% and 50% lines match the amber and red zones of the gauge.
- The banner was congested, its letters (made of digits) were unreadable at normal window widths, and stray 0s and 1s appeared below the title. A title of 20 letters built from digits is only about 5 digits per letter at that width, so no tuning could make it legible. The title is now drawn as real, crisp, measured text, and the digits are only a faint sparse texture that stays clear of the letters and the frame. In a test run of the banner script at four widths (1320, 900, 480 and 360 px) the title was readable each time and at most 4 digits fell inside the title area (they sit beside letters, not on them).
- With placeholder values the seed bar chart is flat (all zeros). The five seed numbers are now also printed under the chart.
- The disagreement gauge sat tight against the heading below it. It has more space now.

## 7. Sign-off

Tested by (Member 4): ______________________  Date: ____________

Reviewed by (Member 3): ______________________  Date: ____________
