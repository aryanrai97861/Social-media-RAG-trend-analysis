# SocialTrendAnalyzer

A Retrieval-Augmented Generation (RAG) system for social media trend analysis.

It ingests social media (Reddit, RSS), extracts entities, computes trending topics with z-scores and growth metrics, indexes contextual documents for RAG, and provides a Streamlit dashboard and alerting hooks.

Features
- Multi-source ingestion (Reddit, RSS)
- Entity extraction, tokenization, URL/HTML cleaning
- Trend detection (z-score, growth, velocity)
- Context indexing for RAG (Chroma + sentence-transformers)
- Alerts via email/webhook (opt-in via env vars)

Quickstart (local)
1. Clone:
```bash
git clone <repo-url>
cd SocialTrendAnalyzer
```
2. Create venv and install:
```bash
python -m venv .venv
source .venv/Scripts/activate   # use .venv\Scripts\activate.bat on Windows cmd
pip install --upgrade pip
pip install -r requirements.txt
```
3. Configure env vars: create a `.env` (see `setup.md` for example).
4. Initialize DB (one-time):
```bash
python database/schema.py --init
```
5. Backfill / Reprocess & Refresh trends:
```bash
python scripts/reprocess_entities.py
python scripts/refresh_trends.py --verbose
```
6. Run dashboard:
```bash
streamlit run app.py
```

Docker (quick demo)
```bash
docker build -t social-trend-analyzer .
docker run -p 8501:8501 --env-file .env social-trend-analyzer
```

Deployment notes
- For demos use Streamlit Cloud or Hugging Face Spaces (ensure `requirements.txt` present and set secrets).
- For production, use Postgres (set `DB_URL`) and a container host (Cloud Run, ECS, etc.).
- Alerts are disabled unless `ALERT_*` env vars are set.

Files of interest
- `pipeline/` — ingestion, normalization, entity extraction, features
- `scripts/` — reindexing, reprocessing, refresh_trends
- `rag/` — embeddings and retriever
- `database/` — schema and DB utilities
- `app.py` — Streamlit dashboard entrypoint
- `setup.md` — full setup & deployment instructions

Contributing
- Open an issue or PR. Add tests and update `requirements.txt` when adding new dependencies.

License
- MIT (or choose your own) — add LICENSE if required.
