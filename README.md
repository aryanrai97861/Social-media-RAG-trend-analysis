# 🌐 Social Media RAG & Trend Analysis

A comprehensive Retrieval-Augmented Generation (RAG) system that analyzes trending topics across social media platforms, providing AI-powered contextual insights and real-time monitoring capabilities.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.37.1-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

### 📱 Multi-Platform Data Ingestion
- **Reddit Integration**: Real-time ingestion from multiple subreddits
- **RSS Feed Processing**: Automated content aggregation from news sources
- **Extensible Architecture**: Easy to add new social media platforms

### 📈 Advanced Trend Analysis
- **Statistical Trend Detection**: Z-score based trending topic identification
- **Real-time Monitoring**: Continuous analysis of social media conversations
- **Platform Comparison**: Cross-platform trend correlation and analysis
- **Historical Tracking**: Trend evolution over time

### 🤖 AI-Powered Contextual Understanding
- **RAG Architecture**: Retrieval-Augmented Generation for contextual explanations
- **Cultural Knowledge Base**: Curated content about internet culture and memes
- **Wikipedia Integration**: Automatic fetching of relevant background information
- **Local AI Models**: Privacy-focused, no external API dependency (optional OpenAI integration)

### 🚨 Intelligent Alerting
- **Real-time Notifications**: Email and webhook alerts for significant trends
- **Configurable Thresholds**: Customizable alert criteria
- **Content Safety**: Built-in filtering for inappropriate content
- **Trend Change Detection**: Alerts for sudden trend shifts

### 📊 Interactive Dashboard
- **Multi-page Streamlit Interface**: Intuitive web-based dashboard
- **Real-time Visualizations**: Dynamic charts and trend displays
- **Topic Explorer**: Search and analyze specific topics with AI explanations
- **Alert Management**: Configure and monitor alert settings

## 🛠️ Technology Stack

### Core Technologies
- **Backend**: Python 3.8+, SQLAlchemy, SQLite
- **Frontend**: Streamlit, Plotly, HTML/CSS
- **AI/ML**: Transformers, Sentence-Transformers, ChromaDB
- **Data Processing**: Pandas, NumPy, Scikit-learn

### AI Models
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (default)
- **Text Generation**: google/flan-t5-base (default)
- **Optional**: OpenAI GPT-4 and text-embedding-3-large

### Data Sources
- **Reddit API**: PRAW (Python Reddit API Wrapper)
- **RSS/Atom Feeds**: feedparser
- **Wikipedia**: wikipedia-api
- **Extensible**: Plugin architecture for new sources

## 📦 Installation

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd social-rag-trends

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install streamlit praw feedparser pandas numpy scikit-learn
pip install sentence-transformers chromadb wikipedia transformers
pip install torch sqlalchemy python-dotenv plotly requests

# Create directories
mkdir -p data/chroma context/wikipedia_cache logs

# Copy configuration
cp .env.example .env
