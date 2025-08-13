# Social Media RAG & Trend Analysis

## Overview

This is a comprehensive Retrieval-Augmented Generation (RAG) system that analyzes trending topics across social media platforms, providing AI-powered contextual insights and real-time monitoring capabilities. The system ingests content from Reddit and RSS feeds, detects statistical trends using z-score analysis, and provides intelligent explanations for viral content through a curated knowledge base of internet culture and social movements.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit-based multi-page web application
- **Dashboard Pages**: Trends Dashboard, Topic Explorer, and Alerts & Monitoring
- **Visualization**: Plotly charts for trend analysis and real-time data display
- **Components**: Modular card-based UI components for trends and posts

### Backend Architecture
- **Database**: SQLAlchemy ORM with SQLite for relational data storage
- **Vector Database**: ChromaDB for semantic search and document retrieval
- **Pipeline**: Modular ingestion pipeline with separate components for Reddit and RSS
- **Content Processing**: Feature extraction, normalization, and trend analysis modules

### Data Storage Solutions
- **Primary Database**: SQLite with three main tables (posts, trends, alert_history)
- **Vector Store**: ChromaDB for embeddings and contextual document retrieval
- **Caching**: Wikipedia content caching for offline contextual information
- **File Storage**: Markdown-based curated content for cultural knowledge

### AI/ML Components
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 for semantic understanding
- **Text Generation**: google/flan-t5-base for contextual explanations
- **Trend Detection**: Statistical analysis using z-scores and exponential weighted moving averages
- **Content Safety**: Built-in filtering for profanity, spam, hate speech, and misinformation

### Authentication and Authorization
- **Current State**: No authentication system implemented
- **API Security**: Reddit API integration using client credentials
- **Content Filtering**: Multi-layer content safety system with configurable thresholds

### Data Processing Pipeline
- **Ingestion**: Real-time content collection from Reddit subreddits and RSS feeds
- **Normalization**: Standardized post structure across different platforms
- **Feature Extraction**: Hashtag detection, entity recognition, and content analysis
- **Trend Analysis**: Time-series analysis with configurable windows and baselines
- **Alerting**: Email and webhook notifications for significant trend changes

## External Dependencies

### Third-Party APIs
- **Reddit API**: PRAW library for real-time subreddit content ingestion
- **RSS Feeds**: feedparser for news and blog content aggregation
- **Wikipedia API**: Automated fetching of background information for context
- **Optional OpenAI API**: Enhanced text generation capabilities

### AI Model Dependencies
- **Hugging Face Transformers**: Core ML framework for local model inference
- **Sentence Transformers**: Embedding generation for semantic similarity
- **ChromaDB**: Vector database for similarity search and retrieval
- **PyTorch**: Backend framework for neural network operations

### Notification Services
- **SMTP Email**: Configurable email alerts for trend notifications
- **Webhooks**: HTTP-based notifications for custom integrations
- **Platform APIs**: Future integration points for Discord, Slack, or other services

### Data Sources
- **Reddit Platforms**: Multiple subreddit monitoring for social trends
- **RSS/Atom Feeds**: News aggregation from major outlets (BBC, CNN, TechCrunch)
- **Curated Knowledge Base**: Markdown files containing internet culture context
- **Wikipedia Integration**: Automatic context retrieval for trending topics

### Infrastructure Dependencies
- **SQLite**: Lightweight relational database for structured data
- **Streamlit**: Web application framework for dashboard interface
- **Plotly**: Interactive visualization library for charts and graphs
- **Pandas/NumPy**: Data manipulation and statistical analysis