# Repository Guidelines

## Project Structure & Module Organization
- `app/` hosts the FastAPI service; routers in `api/` call `crud/`, `models/`, and `schemas/`, while `main.py` mounts static assets and runs `init_db()`.
- `database/connection.py` defines the SQLAlchemy engine used by `swimming_pools.db`; refresh the file after schema changes.
- `frontend/` contains the shipped SPA (`index_refactored.html` plus `css/`, `js/`, `data/`) served by the root route.
- Data pipelines live in `crawler/`, whose scripts (e.g. `advanced_crawler.py`) emit JSON input for `load_data_to_db.py` and utilities in the repo root.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs FastAPI, SQLAlchemy, and crawler clients; run inside a Python 3.10+ virtualenv.
- `python load_data_to_db.py swimming_pools.json` seeds SQLite; swap in `advanced_pools.json` after crawling.
- `uvicorn app.main:app --reload` boots the API with live reload; `curl http://localhost:8000/health` should return `{"status": "healthy"}`.
- `python test_system.py` runs a smoke test against the live server and prints sample payloads.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; use `snake_case` for functions and `PascalCase` for Pydantic models.
- Keep response models in `schemas/` and SQLAlchemy tables in `models/`; use explicit `app.*` imports to avoid circular dependencies.
- Add type hints and concise docstrings whenever behaviour extends beyond simple CRUD.

## Testing Guidelines
- Start Uvicorn before running `python test_system.py`; it posts a sample pool and hits `/api/pools` plus `/api/pools/search`.
- Prefer pytest-style modules under `tests/` for new logic, while retaining `test_system.py` for integration smoke coverage.
- After updating datasets, query `/api/pools` to confirm `is_active`, coordinates, and pricing fields support proximity filters.

## Commit & Pull Request Guidelines
- Mirror the existing format: capitalised prefixes such as `Fix: …`, `Feat: …`, or `Chore: …` with subjects under ~72 characters.
- Commit runtime code, migrations, and regenerated JSON together when they are coupled; avoid mixing crawler and frontend changes.
- PRs should summarise intent, list test commands executed, link issues or data sources, and add screenshots for UI tweaks.

## Security & Configuration Tips
- Keep secrets out of Git: Kakao Map keys stay in `frontend/data/config.json`; backend credentials (`DATABASE_URL`, Naver keys, `ANTHROPIC_API_KEY`) live in a local `.env`.
- Review crawler output for personal data before committing and favour public or aggregated fields.
- On Render, verify `render.yaml` uses the intended dataset and listens on port `10000`.
