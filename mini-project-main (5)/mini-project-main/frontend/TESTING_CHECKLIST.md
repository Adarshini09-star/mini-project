# SIH26153 Frontend: Testing Checklist (Phase 5)

Run everything from inside the `frontend/` folder.

```
python -m unittest discover -s tests -v      # automated tests: all must say OK (73 at the time of writing)
python -m streamlit run app.py               # opens http://localhost:8501
```

Status key: **PASS** = seen working (screenshot or test). **TODO** = not tested yet. Change TODO to PASS only after you have seen it yourself.

## A. Things already seen working

| # | Check | How it was verified | Status |
|---|---|---|---|
| 1 | Dashboard renders (cream and black) | Screenshots, Demo mode | PASS |
| 2 | Navigation: Forecast dashboard / About the model | Screenshots, all 4 About tabs opened | PASS |
| 3 | Chart shows the 5 entered minutes plus the t+1 point, with 25% and 50% lines | Screenshots (t+1 was a placeholder in Demo mode) | PASS |
| 4a | CSV upload accepts a valid file and shows "Input looks valid" | Screenshots | PASS |
| 7a | Backend not running: clear "Cannot reach the backend" error, no fake result | Screenshots (health check and Get forecast) | PASS |
| 10 | Model warnings are visible | Screenshots (MOCK advisories) | PASS |
| 12 | Demo/MOCK values are never shown as real: red banner, `[MOCK]` next to percentage and state, placeholder notes | Screenshots | PASS |

## B. Still to test

### B1. CSV validation with BAD files (item 4)
Make small CSV files (copy your good sample and break one thing each time). Upload each one. Expected: a red error that explains the problem, and the **Get forecast** button disabled.

| Break this | Expected message starts with | Status |
|---|---|---|
| Delete the `Total_Flows` column | Missing required traffic columns | TODO |
| Keep only 4 rows | Window must contain exactly 5 rows | TODO |
| Put `-5` in any value | Negative values are invalid | TODO |
| Put `150` in `Bot_Pct` | Bot percentage must be between 0.0% and 100.0% | TODO |
| Change one timestamp so a gap is 2 minutes | Time gap detected | TODO |
| Put the word `abc` in a number cell | A cell that should hold a number contains text | TODO |
| Upload a `.txt` renamed to `.csv` with random text | The file could not be read as a CSV table | TODO |

### B2. Real backend (items 5, 6, 7b, 8, 9). Needs Member 3's server running

Steps: start the backend (command from Member 3), turn **Demo mode OFF**, set **Backend address** if the port is not 8000.

| # | Check | Expected | Status |
|---|---|---|---|
| 5 | Click **Check backend connection** | Backend status ok, model status PROVISIONAL, no red banner | TODO |
| 5 | Click **Get forecast** with valid data | A forecast appears | TODO |
| 6 | Watch right after clicking | A "Waiting for the forecast..." spinner shows briefly | TODO |
| 8 | Compare the card's percentage with "Raw response from the API" (open the expander) | Same number, 2 decimals | TODO |
| 9 | Compare the state badge with the raw `predicted_state` | Same state. Below 25 = Low, 25 to below 50 = Medium, 50 or above = High | TODO |
| 9 | Try the "Busy traffic (example)" preset | A higher percentage than "Quiet traffic" | TODO |
| 10 | Check the Model advisories box | Shows every string in the raw `warnings` list | TODO |
| 12 | Look for `[MOCK]` and the red banner | Must NOT appear (unless the backend itself says MOCK, then it MUST appear) | TODO |
| 7b | Send an invalid window to the backend (e.g. use the table and set Bot_Pct to 150 only if the frontend lets it through) | The frontend blocks it first; if the backend returns 422 the message is friendly | TODO |
| 7c | Stop the backend, click Get forecast | "Cannot reach the backend" error | PASS (seen) |

If anything differs from the table, copy the screenshot or error text to your team and to me. Do not change code until the cause is known.

### B3. Responsive layout (item 11)
1. In the browser press `F12`, then the device toolbar button (or just drag the window narrow).
2. Check at about 1400, 900 and 400 pixels wide.
3. Expected: the forecast card and gauge stack vertically on narrow widths, tables scroll sideways inside their box instead of breaking the page, text stays readable, the sidebar can be opened and closed. Status: TODO.

## C. Wording rules to confirm by eye
- Nowhere says "real-time detection", "confidence", "certainty", "accuracy" (for Model Disagreement) or "SHAP". (Automated tests also check this.)
- The PROVISIONAL banner is at the top of both pages.
- The Low-state recall note is visible under the forecast and at the foot of both pages.

## D. Git: safe workflow

> Do not push to `main`. Do not commit `.env` files, keys or passwords.

1. Check you are inside a Git repository: `git status`.
   If it says "not a git repository", your folder came from a downloaded zip. Clone the team repo into a new folder, copy the changed frontend files into the clone, and continue there.
2. See your branch: `git branch`.
3. Get the latest team changes: `git fetch origin`, then `git pull origin main` while on main (before creating your branch).
4. Create your branch: `git checkout -b member4-frontend-dashboard`.
5. Stage only your files:
   ```
   git add frontend/app.py frontend/display.py frontend/about_page.py frontend/ui_text.py frontend/README.md
   git add frontend/tests/test_display.py frontend/tests/test_about.py frontend/TESTING_CHECKLIST.md
   ```
6. Check `git status`. Staged files must NOT include `__pycache__`, `.env`, `frontend_backup*` or `frontend_github_backup`.
7. Commit: `git commit -m "Frontend: forecast display, About page, navigation, tests"`.
8. Push your branch: `git push -u origin member4-frontend-dashboard`.
9. On GitHub click **Compare & pull request**, describe the change in a few lines, request a review from Member 3, and do not merge it yourself.
10. If Git reports a merge conflict, stop and send the message to your team and to me. Do not guess a resolution.

Optional: add a line `.env` to `.gitignore` (it currently ignores `.venv/`, `__pycache__/`, `*.pyc`, `sample_window.csv` and the model folder, but not `.env`).
