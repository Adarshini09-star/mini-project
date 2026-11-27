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
- `app.py`: the Streamlit page (Phase 1: connection test)
- `api_client.py`: all HTTP calls, error handling, Demo mode
- `ui_text.py`: every message shown to the user (safety wording, error messages)
- `.streamlit/config.toml`: colour theme
