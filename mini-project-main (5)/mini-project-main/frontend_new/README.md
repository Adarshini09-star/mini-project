# Frontend (Member 4): bot traffic forecast dashboard

Talks to the backend only through HTTP (`GET /health`, `POST /predict`, see `../docs/API_CONTRACT.md`).
It never loads the model, the scalers or `predict_lstm.py`.

## Run (from inside this folder)
    pip install -r requirements.txt
    python -m streamlit run app.py

Backend not ready yet? Switch on **Demo mode** in the sidebar. It shows placeholder values from the API contract,
clearly labelled as not real forecasts.

## Test
    python -m unittest discover -s tests -v
    python tests/app_flow_check.py      # checks what the page shows in each situation (needs ../predict_lstm.py and ../docs)
    python tests/backend_check.py --url http://localhost:8000   # checks a RUNNING backend (see TEST_RECORD.md section 5)

## Files
- `app.py`: the Streamlit page (tabs: Forecast / Traffic Analytics / About the Model; also draws the banner and the cream / black switch)
- `api_client.py`: all HTTP calls, error handling, Demo mode
- `display.py`: turns a forecast response into the card, gauge, charts and plain-language statements, and prepares the analytics tables and charts
- `validation.py`: checks the 5-row input (same rules and codes as the backend validator) and reads CSV files
- `ui_text.py`: every message shown to the user (safety wording, error messages)
- `hero_banner.py`, `theme_switch.py`: the decorative banner and the cream / black switch (see the section below)
- `.streamlit/config.toml`: colour themes
- `TEST_RECORD.md`: what was tested, the 12 brief items, a manual browser checklist, and the backend integration steps

## Banner and cream / black switch
`hero_banner.py` draws a classic dark banner at the top of the page (Canvas2D, runs in the browser, same look on both page
colours). The title is real, crisp serif capitals (ivory with a soft green glow) inside a thin double frame, so the letters are
easy to read at any window width (two lines on narrow screens). A faint, sparse texture of green 0s and 1s with a few thin falling
trails sits behind it and fades out around the title. It is decorative only and never shows forecast values. Tune it in the
`CONFIG` dict at the top of the file (`title`, `fill`, `rainDensity`, `cellSize`, colours, `vignette`, `height`). People whose
system asks for reduced motion see one still frame.

The first switch in the sidebar ("Black background") makes the whole page light cream or black. Streamlit cannot change its
theme from Python, so `theme_switch.py` saves the choice in the browser and reloads the page once (anything typed into the
table is reset by that reload). Both palettes are in `.streamlit/config.toml`; Streamlit's own Settings menu also works.
