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

## Files
- `app.py`: the Streamlit page (sidebar navigation, backend check, traffic data input, forecast request, forecast display)
- `about_page.py`: the "About the model" page (Phase 4); its text and figures live in `ui_text.py`
- `display.py`: pure helpers for the forecast display (card, Model Disagreement gauge, chart data); no Streamlit, no model code
- `api_client.py`: all HTTP calls, error handling, Demo mode
- `validation.py`: checks the 5-row input (same rules and codes as the backend validator) and reads CSV files
- `ui_text.py`: every message shown to the user (safety wording, error messages)
- `.streamlit/config.toml`: colour theme

## Page background: falling code rain, title and cream / black switch
`page_background.py` draws "BOT / TRAFFIC / FORECAST" as huge text behind the page, with binary code rain falling over the
WHOLE background. The rain lights up where it passes through the title letters, which are also filled with faint binary.
It is fixed (stays while you scroll), follows the sidebar opening and closing, never blocks clicks, and never shows forecast
values. People whose system asks for reduced motion see one still frame.

The first switch in the sidebar ("Black background") flips the whole page between light cream and black. Streamlit cannot
change its theme from Python, so the switch saves the choice in the browser and reloads the page once (anything typed
into the table is reset by that reload). Both palettes are in `.streamlit/config.toml`; Streamlit's own Settings menu
also works. Tune it at the top of `page_background.py`: `RAIN` (cellSize, trail, rainOpacity, animSpeed, animIntensity)
and `PALETTES` (title strength `inkOpacity`, panel behind the content `panelOpacity`, rain colours).
