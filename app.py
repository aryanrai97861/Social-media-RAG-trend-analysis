import streamlit as st
import os
from pathlib import Path
from utils.config import load_config
from database.schema import init_database
import warnings

warnings.filterwarnings('ignore')

# Configure page
st.set_page_config(
    page_title="Social Media RAG & Trend Analysis",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
config = load_config()

# Initialize database and directories
def setup_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        "data",
        "data/chroma",
        "context/wikipedia_cache",
        "logs"
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def main():
    setup_directories()
    init_database()
    
    st.title("🌐 Social Media RAG & Trend Analysis")
    st.markdown("""
    Welcome to the Social Media RAG system! This application helps you:
    
    - **📱 Ingest** social media content from Reddit and RSS feeds
    - **📈 Analyze** trending topics and viral content
    - **🔍 Explore** contextual information about social movements and memes
    - **🚨 Monitor** real-time trends with intelligent alerts
    """)
    
    # Sidebar navigation info
    with st.sidebar:
        st.header("Navigation")
        st.markdown("""
        Use the pages in the sidebar to:
        
        **📈 Trends Dashboard**
        - View real-time trending topics
        - Analyze trend patterns over time
        - Monitor viral content
        
        **🔎 Topic Explorer**
        - Search and explore specific topics
        - Get AI-powered contextual analysis
        - Understand cultural significance
        
        **🚨 Alerts**
        - Configure trend alerts
        - Monitor significant changes
        - Set up notifications
        """)
        
        # System status
        st.header("System Status")
        
        # Check database connection
        try:
            from database.schema import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute("SELECT COUNT(*) as count FROM posts").fetchone()
                post_count = result[0] if result else 0
            st.success(f"✅ Database Connected ({post_count} posts)")
        except Exception as e:
            st.error(f"❌ Database Error: {str(e)}")
        
        # Check ChromaDB
        try:
            import chromadb
            client = chromadb.PersistentClient(path=config.get('CHROMA_PATH', './data/chroma'))
            collections = client.list_collections()
            st.success(f"✅ ChromaDB Connected ({len(collections)} collections)")
        except Exception as e:
            st.error(f"❌ ChromaDB Error: {str(e)}")
    
    # Main content area
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📊 Quick Stats")
        try:
            from database.schema import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                # Total posts
                result = conn.execute("SELECT COUNT(*) as count FROM posts").fetchone()
                total_posts = result[0] if result else 0
                st.metric("Total Posts", f"{total_posts:,}")
                
                # Recent posts (last 24h)
                result = conn.execute("""
                    SELECT COUNT(*) as count FROM posts 
                    WHERE datetime(created_at) > datetime('now', '-1 day')
                """).fetchone()
                recent_posts = result[0] if result else 0
                st.metric("Recent Posts (24h)", f"{recent_posts:,}")
                
        except Exception as e:
            st.error(f"Error loading stats: {str(e)}")
    
    with col2:
        st.subheader("🔥 Top Platforms")
        try:
            from database.schema import get_engine
            import pandas as pd
            engine = get_engine()
            df = pd.read_sql("""
                SELECT platform, COUNT(*) as count 
                FROM posts 
                GROUP BY platform 
                ORDER BY count DESC 
                LIMIT 5
            """, engine)
            if not df.empty:
                st.dataframe(df, hide_index=True)
            else:
                st.info("No data available yet. Run data ingestion first.")
        except Exception as e:
            st.error(f"Error loading platform data: {str(e)}")
    
    with col3:
        st.subheader("⚡ Actions")
        
        if st.button("🔄 Run Data Ingestion", type="primary"):
            with st.spinner("Ingesting data..."):
                try:
                    # Run Reddit ingestion
                    from pipeline.ingest_reddit import run as run_reddit
                    from pipeline.ingest_rss import run as run_rss
                    
                    run_reddit(limit_per_sub=50)
                    run_rss()
                    
                    st.success("✅ Data ingestion completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ingestion failed: {str(e)}")
        
        if st.button("📈 Refresh Trends"):
            with st.spinner("Computing trends..."):
                try:
                    from scripts.refresh_trends import main as refresh_trends
                    refresh_trends()
                    st.success("✅ Trends refreshed!")
                except Exception as e:
                    st.error(f"❌ Trend refresh failed: {str(e)}")
        
        if st.button("📚 Index Context"):
            with st.spinner("Indexing context..."):
                try:
                    from scripts.index_context import main as index_context
                    index_context()
                    st.success("✅ Context indexed!")
                except Exception as e:
                    st.error(f"❌ Context indexing failed: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        Social Media RAG & Trend Analysis System v1.0
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
