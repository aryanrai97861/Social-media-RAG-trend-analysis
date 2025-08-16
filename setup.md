# Social Media RAG & Trend Analysis - Setup Guide

This guide will walk you through setting up the Social Media RAG (Retrieval-Augmented Generation) system for analyzing trending topics across social media platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Initial Setup](#initial-setup)
5. [Running the Application](#running-the-application)
6. [Productionization & Deployment](#productionization--deployment)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Required Software
- Python 3.11 (recommended)
- Git (for cloning the repository)
- pip (Python package installer)

### System Requirements
- RAM: 4GB minimum, 8GB recommended
- Storage: 2GB free space minimum
- Internet: Stable connection for data ingestion and AI models

### Optional Requirements
- Reddit API Account (for Reddit data ingestion)
- Email Account (for alert notifications)
- Webhook URL (for custom notifications)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SocialTrendAnalyzer
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/Scripts/activate   # On Windows with Git Bash; use .venv\\Scripts\\activate.bat for cmd.exe
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with environment variables. Example:

```ini
# Database (SQLite file for demo)
DB_PATH=./data/social.db

# Reddit (optional)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=SocialTrendAnalyzer/1.0

# Alerts (optional) - leave blank to keep alerts disabled
ALERT_EMAIL_SMTP=smtp.gmail.com
ALERT_EMAIL_USER=
ALERT_EMAIL_PASS=
ALERT_EMAIL_TO=
ALERT_WEBHOOK_URL=
```

## Initial Setup

Initialize the database (tables and indexes) and optionally backfill data:

```bash
python database/schema.py --init
# or run any backfill/ingest scripts
python pipeline/backfill_seed.py
```

## Running the Application

To reprocess entities and refresh trends locally:

```bash
python scripts/reprocess_entities.py
python scripts/refresh_trends.py --verbose
```

Start the Streamlit dashboard:

```bash
streamlit run app.py
```

## Productionization & Deployment

This section covers creating a reproducible environment and deploying the demo.

### Prepare environment variables

Create a `.env` in the project root with your configuration (see Configuration above).

### Docker (recommended for demo hosting)

Build and run:

```bash
docker build -t social-trend-analyzer .
docker run -p 8501:8501 --env-file .env social-trend-analyzer
```

### Streamlit Cloud / Hugging Face Spaces

- Ensure `requirements.txt` exists (it does).
- Push the repo to GitHub.
- Create a new Streamlit app or Hugging Face Space and point to this repository. Add required secrets in the UI (DB_PATH, API keys).

### Notes and production guidance

- Alerts: They remain disabled unless `ALERT_*` env vars are set. The notifier logs and returns gracefully when credentials are missing.
- Database: SQLite is suitable for demos. For production switch to Postgres and update `get_engine()` to read a DSN from `DB_URL`.
- Scaling: Add a streaming/queueing layer (Kafka, Pub/Sub) and workers for high-throughput ingestion.

## Troubleshooting

- If Streamlit fails to start, check `requirements.txt` and ensure dependencies installed.
- For DB errors, check `DB_PATH` in `.env` and file permissions.
- Alerts failing is expected if `ALERT_*` env vars are unset; set them to enable.

## Advanced Configuration

- To use a managed vector DB instead of Chroma, update `rag/` indexing code and `rag/embeddings.py` to point to your provider.
- To add new ingestion sources, create a `pipeline/ingest_<source>.py` script and follow the pattern used by `ingest_reddit.py` and `ingest_rss.py`.
