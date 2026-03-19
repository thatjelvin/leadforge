# LeadForge

Minimal runnable implementation based on `PRD.md` and `architecture.md`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000` and docs at `http://127.0.0.1:8000/docs`.

## Run tests

```bash
pytest -q
```

## Docker

```bash
docker compose up --build
```
