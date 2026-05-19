# ThinkLand Consumer Backend

FastAPI backend for the ThinkLand consumer app.

## Local setup

1. Create MySQL schema with `sql/init.sql`.
2. Create `.env` from `.env.example`.
   Generate `API_KEY_ENCRYPTION_KEY` with:

```bash
.venv\Scripts\python scripts\generate_fernet_key.py
```

3. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

4. Start the API:

```bash
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```
