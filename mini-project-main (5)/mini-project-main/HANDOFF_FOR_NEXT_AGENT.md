# Handoff: SIH26153 Bot Traffic Forecast dashboard (Member 4 frontend)

Written for a new Claude conversation that continues this project. Read all of it before doing anything.

## 0. What the user should give the new agent

1. **This file** (paste it into the chat or upload it).
2. **The latest `mini-project-main.zip`** (the whole repo with the finished `frontend_new/` folder inside).
3. **Screenshots** of anything that looks wrong, plus the output of any command that failed.

Then paste this as the first message:

> You are taking over as senior frontend developer, tester and technical mentor for Member 4 of team project SIH26153 (AI-based bot traffic forecasting). I am a student on Windows. I am attaching HANDOFF_FOR_NEXT_AGENT.md and the latest repo zip. Read the handoff fully, unzip the repo, run the unit tests and the page-flow check from section 5 to confirm the state it describes, then tell me in plain language what is done and what is left. The folder to work in is `frontend_new` (ignore the other frontend folders). Work in small steps, give exact commands and exact file paths, never claim something works until it has been tested or I have sent a screenshot, and deliver changes as a zip that keeps the folder layout so I can copy it over mine.

## 1. Project and roles

- **Project:** SIH26153, AI-based network attack forecasting. In practice the system forecasts the **bot-traffic share of the next minute** from the last 5 one-minute records and maps it to Low / Medium / High. It is offline and batch only, provisional, and it does **not** detect attacks.
- **Member 1:** dataset (CSE-CIC-IDS2018). Gaps: audit of some files incomplete; units of `Avg_Duration_Bot` and the exact definition of `Bot_Pct` still unconfirmed.
- **Member 2:** ML (LSTM ensemble of 5 seeds 42 to 46, baselines, `predict_lstm.py`, model package zip). Known weakness: Low-state recall was about 0% on the test day.
- **Member 3:** architecture docs (`docs/`) and the backend (FastAPI). The docs are merged into the team repo. **The backend code was not pushed to GitHub at the time of writing** (branch `member3-backend-api` is only on Member 3's computer).
- **Member 4 = the user:** frontend and testing. Dashboard shows traffic information, predicted state, risk/disagreement and explanations.

## 2. About the user and how to work with them

- Student, Windows, Python 3.11, VS Code, Microsoft Edge. Wants **step-by-step help with exact commands and file paths**.
- Said repeatedly: "no space for mistakes". So: verify before handing over, say plainly what was **not** verified, and never claim a visual result without a screenshot.
- Delivers by **zip files**. Put changed files in the right folders and tell them exactly where to copy them. They send **screenshots** to confirm; read them carefully (they have caught real issues).
- They often send many screenshots at once. Match each one to the checklist item it proves, and say what is still not shown.
- Keep answers short and clear. One question at most per message.

## 3. Current state (end of this conversation)

All five planned phases are built in the folder **`frontend_new/`** of the team repo:

1. Backend client with Demo mode. 2. Input window (editable table, CSV upload) with validation. 3. Forecast card, state badge, Model Disagreement gauge, seed chart, advisories. 4. Traffic Analytics tab and About the Model tab. 5. Test record, backend integration check, stricter tests.

Also in the folder, kept from the user's own work: the **cream / black switch** (`theme_switch.py`, two palettes in `.streamlit/config.toml`) and the **decorative banner** (`hero_banner.py`, now redesigned, see 3a).

**Test status (run from the final zip, Python 3.12 in the sandbox):** 93 unit tests pass and 18 page scenarios pass. Everything outside `frontend_new/` in the repo is byte-identical to what the user uploaded.

**Screenshot-confirmed in the user's browser:** page layout, banner (earlier versions), cream and black themes, Demo mode forecast card with `[MOCK]` tags, gauge, advisories, seed numbers, observed-and-forecast chart, Analytics tab (cards, charts, tables), About tab, backend-unreachable error, out-of-date notice, bad time label error, CSV valid, plain-text file rejected.

### 3a. The banner (last change)

The old banner made the title from falling 0s and 1s. At normal widths 20 letters from digits were unreadable, and a small subtitle line turned into stray digits. The new `hero_banner.py` draws the title as **real crisp ivory serif capitals** (soft green glow, thin double frame, two lines on narrow screens). A faint sparse 0/1 texture and a few thin falling trails sit behind it and fade out around the title and frame. It was checked by running the banner's real JavaScript in Node with a recording canvas and rendering the result at 1320, 900, 480 and 360 px widths (title readable every time). **The user has not yet seen the final banner in their browser.**

### 3b. Still not confirmed by the user

- The final banner in the browser (checklist M17).
- Typing a negative number, 130 in Bot_Pct and a blank cell (M5); CSVs with a time gap, fewer than 5 rows, a missing column (M9); a narrow browser window (M15); the "Busy traffic" preset on the Analytics tab; chart colours after the last change.
- **Whether Phases 2 to 5 are committed and pushed** (only the Phase 1 commit `d533a6c` was shown). Ask for `git log --oneline -8` and `git status` from `C:\Projects\mini-project`.
- **Anything against the real backend** (section 8).

## 4. Where things are

**Team repo:** `https://github.com/Adarshini09-star/mini-project` (the user pushed the branch `frontend-dashboard` there once; the rule is never to push to `main`).
**The user's safe clone:** `C:\Projects\mini-project`. Working branch: **`frontend-dashboard`** (pushed once with Phase 1). Never push to `main`.

### Git trap (important)
The user's Downloads folders (`...\Downloads\mini-project-main (N)\...`) sit **inside a different git repository**: a repo in their home folder whose remote is `flood_inun` (a different project). VS Code opened on those folders shows `main*  29↓ 5↑`. **Committing or pushing from there would go to the wrong project.** Always commit from `C:\Projects\mini-project`:

```
cd C:\Projects\mini-project
git branch                 # must show frontend-dashboard
git status                 # must list only files inside frontend_new/
git add frontend_new
git commit -m "..."
git push
```
To confirm which repo a folder belongs to: `git rev-parse --show-toplevel` and `git remote -v`.

### Repo layout (zip top folder `mini-project-main/`)
`docs/` (Member 3's 7 documents), `predict_lstm.py`, ML files, model package zips, and several frontend folders. **Only `frontend_new/` is current.** Ignore `frontend/`, `frontend_backup/`, `frontend_backup1/`, `frontend_github_backup/`. Do not delete them without asking.

### `frontend_new/` file map
| File | Purpose |
|---|---|
| `app.py` | Streamlit page: three tabs (Forecast, Traffic Analytics, About the Model), sidebar (black switch, Demo mode, backend address) |
| `api_client.py` | All HTTP calls (`fetch_health`, `request_forecast`), error handling, Demo mode returns the contract's MOCK payload |
| `validation.py` | Client-side checks mirroring `predict_lstm.validate_window` (same codes, same order), CSV reading (last 5 rows), presets |
| `display.py` | Forecast card HTML, gauge, seed series, charts and colours, explanations, analytics tables, observed-state rule |
| `ui_text.py` | All user-facing wording: banners, notices, error messages, About text |
| `hero_banner.py` | Decorative banner (never shows forecast values) |
| `theme_switch.py` | Cream / black switch (user's own code; keep it) |
| `.streamlit/config.toml` | Two colour palettes |
| `requirements.txt` | `streamlit==1.67.0`, `requests==2.34.2` |
| `TEST_RECORD.md` | What was tested, the 12 brief items, manual browser checklist M1 to M18 (the user fills Result), backend steps |
| `tests/` | `test_api_client.py` (19), `test_validation.py` (20), `test_display.py` (31), `test_backend_check.py` (10), `test_hero_banner.py` (9), `test_theme_switch.py` (4), `app_flow_check.py` (18 scenarios), `backend_check.py` (script for a running backend) |

## 5. How to run and verify

User's machine (PowerShell), from `...\frontend_new`:
```
python -m unittest discover -s tests          # expect: Ran 93 tests ... OK
python tests\app_flow_check.py                # expect: SMOKE OK
python -m streamlit run app.py                # open http://localhost:8501
```
Tests read `../docs/` and `../predict_lstm.py`, so run them inside the repo layout (`frontend_new` next to `docs` and `predict_lstm.py`). Without them, some tests skip.

**Sandbox method used (no Streamlit or TensorFlow there):**
- A **stand-in backend** (in `tests/test_api_client.py`) uses the real `validate_window()` and the contract's example response, so the client is tested against the repo's own rules.
- `tests/app_flow_check.py` runs `app.py` against a **recording stand-in for Streamlit** (checks what the page shows in each situation, not how it looks).
- The banner was checked with a throwaway Node + Pillow harness (not shipped).
- Always rebuild deliverables from a scratch copy that includes `docs/` and `predict_lstm.py`, re-run both checks from the final zip, and confirm the other repo files are unchanged (`cmp` against the user's upload; use `bash` with `read -d ""` because one file name has spaces: `miniproject_CLEAN_v1 (1).ipynb`).

## 6. Rules the code must keep (from `docs/FRONTEND_HANDOFF.md`, `API_CONTRACT.md`, `EXPLAINABILITY.md`, and the user's brief)

- The frontend **never loads the model, scaler or `predict_lstm.py`**. All forecasts come from the backend over HTTP.
- **Wording:** never call it real-time or attack detection. A Low or Medium forecast is **never** proof that traffic is safe (Low-state recall about 0%). Call the seed spread **"Model Disagreement"**. Never use the words *confidence, accuracy, certainty, SHAP* (tests scan the files). The hand-off's "High Attack Threat" and "Low Risk" labels are deliberately replaced by neutral ones ("Estimated traffic state", "High bot share forecast").
- **Mock data must never look real:** Demo mode and backend MOCK mode always get a red banner, `[MOCK]` tags next to the number and badge, and no explanations.
- Show the state exactly as the backend sends it (`predicted_state`); never recompute it from the percentage on the forecast card.
- No SHAP: `EXPLAINABILITY.md` concludes it is not defensible. Explanations are plain statements about the input and the response.
- Do not modify the 7 features, the 5-row window or the thresholds. Do not retrain or modify the ML model. Do not touch `docs/` or ML files.

### API contract (summary)
- `GET /health` returns `status, model_version, model_status ("PROVISIONAL" or "MOCK"), package_folder, limitations`.
- `POST /predict` body `{"window": [5 rows]}`, rows oldest first, 60 seconds apart, each with `Timestamp` (optional, recommended) and `Bot_Pct, Total_Flows, Fwd_Pkts_Bot, Bwd_Pkts_Bot, Fwd_Bytes_Bot, Bwd_Bytes_Bot, Avg_Duration_Bot`.
- Success returns `forecast_horizon_minutes, predicted_bot_pct_next_minute, predicted_state, state_thresholds, seed_predictions, seed_spread_pct_points, model_version, model_status, warnings`.
- Errors: HTTP 422 `{error: true, error_code, error_message, model_status}` with codes `MISSING_FEATURES, BAD_SHAPE, NAN_OR_INF, NEGATIVE_VALUE, BOT_PCT_RANGE, BAD_TIMESTAMP, NOT_CONSECUTIVE, BAD_REQUEST`; HTTP 500 `SERVER_ERROR`.
- States: Low below 25, Medium 25 to below 50, High 50 and above (same rule as `predict_lstm.state_from_pct`).
- Disagreement levels (spread in percentage points): up to 5.0 low, up to 10.0 moderate, above 10 high.

## 7. Decisions already made (do not redo without a reason)

- **Keep Streamlit** (it was the existing framework; the team is Python-only). HTML pieces (card, gauge, banner) are drawn with `st.markdown(unsafe_allow_html=True)` or `st.iframe`; markup is built as one line without indentation (indented HTML becomes a code block) and all text is escaped.
- Analytics use **only the 5 input minutes** (the API has no history or upload endpoint). "Observed state" per minute applies the same thresholds to the observed bot share and is labelled as an observation.
- No "bot flows" count is shown (depends on the unconfirmed `Bot_Pct` definition). `Avg_Duration_Bot` is labelled "unit not confirmed yet".
- A forecast counts as **out of date** when the input, Demo mode or the backend address changes.
- Charts: one distinct earthy colour per series; legends kept short; thresholds use the same amber and red as the gauge.

## 8. What is left to do (suggested order)

1. **Make sure the work is saved properly.** Ask for `git status` and `git log --oneline -8` in `C:\Projects\mini-project`. If `frontend_new` is not yet committed on `frontend-dashboard`, guide the copy and commit (section 4). Do not push to `main`.
2. **User finishes the browser checklist** in `TEST_RECORD.md` (items in 3b), then fills the Result column. Update the "Seen so far" column from their screenshots.
3. **Real backend integration (blocked on Member 3).** Member 3's guide used their own paths (`C:\Users\ullas\member3-backend`, a private venv), and the branch `member3-backend-api` was not pushed. When it is pushed: clone it into a **separate** folder (for example `C:\Projects\mini-project-backend`), create a **separate virtual environment** (Member 3 states pandas 2.2.3, TensorFlow 2.21.0, FastAPI 0.163.1, uvicorn 0.54.0; these were not verified), start it from the folder containing `api.py` with `python -m uvicorn api:app --host 127.0.0.1 --port 8000`, then from `frontend_new`:
   ```
   python tests\backend_check.py --url http://localhost:8000
   python tests\backend_check.py --url http://localhost:8000 --compare PATH_TO_UNZIPPED_MODEL_FOLDER
   ```
   Expect `ALL CHECKS PASSED` (a MOCK warning is **not** a real pass). Then run the dashboard with Demo mode off. Record results in `TEST_RECORD.md` section 5. Send mismatches to Member 3 in this form: what I did, expected (contract section), got, raw response.
4. **Pull request:** from `frontend-dashboard` into `main` on GitHub, title "Frontend dashboard (Member 4)", description: all changes are in `frontend_new/`, nothing else touched, runs in Demo mode without a backend, needs Member 3's backend for final integration. Member 3 reviews; the user does not merge it.
5. **Optional polish if the user asks:** the page title below the banner repeats the banner text (offer to shorten it); a flat single-series chart can show a wider time axis than its data (cosmetic, library behaviour); chart colours were not yet seen in the browser.
6. **Team-level items outside the frontend:** Member 1 to confirm the `Bot_Pct` definition and `Avg_Duration_Bot` unit (then a bot-flows count can be added); a final report and demo script do not exist yet.

## 9. Mistakes made in this conversation (avoid repeating)

- A **long-running background server** in the sandbox hung a command. Use `setsid nohup timeout N ... &` with output redirected, or avoid it.
- Deleting scratch folders in the shared outputs folder sometimes failed with an I/O error; use `shutil.rmtree(..., ignore_errors=True)` and tolerate leftovers.
- When the user uploads a new zip, **diff it against the previous upload first** (twice it was identical, and once it contained their own edits that must be kept: `hero_banner.py`, `theme_switch.py`, two-palette `config.toml`).
- I misread "more classic" once and replaced the digit-letter banner with a static masthead; the user wanted the same dark-green digit style but clearer. When a style request is ambiguous, show a preview before building.
- A first design cleanup of the digit-letter banner was not enough: the real problem was resolution (about 5 digits per letter). Measure first, then change.
- A banner preview made with Pillow draws fonts slightly differently from a Windows browser, so say clearly when something is an approximation.
- The user's earlier `git pull` / `checkout` ran in the wrong repo (home folder, remote `flood_inun`). Check `git rev-parse --show-toplevel` before any git advice.

## 10. Things that are NOT in this conversation's outputs but may be mentioned

Old standalone files `explain.py`, `forecast_app.py`, `test_explain.py` and the folder `frontend/` plus `frontend.zip` from the first phases are **obsolete**. They load the model directly or use the old folder name. Do not reuse them.
