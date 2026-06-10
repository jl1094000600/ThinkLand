# ThinkLand Consumer Backend

FastAPI backend for the ThinkLand consumer app.

## Local setup

1. Create MySQL schema with `sql/init.sql`.
2. Create `.env` from `.env.example`.
   Generate `API_KEY_ENCRYPTION_KEY` with:

```bash
.venv\Scripts\python scripts\generate_fernet_key.py
```

If users can choose the platform-provided model, also set:

```env
PLATFORM_AI_BASE_URL=https://api.openai.com/v1
PLATFORM_AI_API_KEY=your-platform-provider-key
PLATFORM_AI_MODEL=gpt-4o-mini
```

Platform models spend user points. Custom user models use the user's own API key and do not spend points.

3. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

4. Start the API:

```bash
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 18080
```
