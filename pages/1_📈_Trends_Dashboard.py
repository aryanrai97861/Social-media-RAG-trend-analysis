import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from database.schema import get_engine
from components.charts import create_trend_chart, create_heatmap
from components.cards import trend_card
from utils.config import load_config

st.set_page_config(
    page_title="Trends Dashboard",
    page_icon="📈",
    layout="wide"
)

config = load_config()

def load_trends_data():
    """Load trending topics from database"""
    try:
        engine = get_engine()
        
        # Load trend data
        trends_df = pd.read_sql("""
            SELECT entity, current_count, baseline_count, trend_score, 
                   growth_rate, created_at, platform
            FROM trends 
            WHERE created_at > datetime('now', '-7 days')
            ORDER BY trend_score DESC
            LIMIT 100
        """, engine)
        
        if trends_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        trends_df['created_at'] = pd.to_datetime(trends_df['created_at'])
        
        # Load time series data
        timeseries_df = pd.read_sql("""
            SELECT DATE(created_at) as date, COUNT(*) as post_count,
                   platform
            FROM posts 
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY DATE(created_at), platform
            ORDER BY date DESC
        """, engine)
        
        timeseries_df['date'] = pd.to_datetime(timeseries_df['date'])
        
        return trends_df, timeseries_df
        
    except Exception as e:
        st.error(f"Error loading trends data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def main():
    st.title("📈 Trends Dashboard")
    st.markdown("Real-time analysis of trending topics across social media platforms")
    
    # Load data
    trends_df, timeseries_df = load_trends_data()
    
    if trends_df.empty:
        st.warning("""
        🔍 No trend data available yet. 
        
        Please:
        1. Run data ingestion from the main page
        2. Wait a few minutes for trend computation
        3. Refresh this page
        """)
        
        if st.button("🔄 Refresh Page"):
            st.rerun()
        return
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_trends = len(trends_df)
        st.metric("Active Trends", total_trends)
    
    with col2:
        hot_trends = len(trends_df[trends_df['trend_score'] > 2.0])
        st.metric("Hot Trends (>2σ)", hot_trends)
    
    with col3:
        avg_growth = trends_df['growth_rate'].mean() if not trends_df.empty else 0
        st.metric("Avg Growth Rate", f"{avg_growth:.1%}")
    
    with col4:
        if not timeseries_df.empty:
            total_posts = timeseries_df['post_count'].sum()
            st.metric("Total Posts (30d)", f"{total_posts:,}")
        else:
            st.metric("Total Posts (30d)", "0")
    
    # Main dashboard content
    tab1, tab2, tab3 = st.tabs(["🔥 Trending Now", "📊 Analytics", "🌍 Platform Breakdown"])
    
    with tab1:
        st.subheader("Top Trending Topics")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            min_score = st.slider("Minimum Trend Score", 0.0, 5.0, 1.0, 0.1)
        with col2:
            platforms = trends_df['platform'].unique() if not trends_df.empty else []
            selected_platforms = st.multiselect("Platforms", platforms, default=platforms)
        with col3:
            top_n = st.selectbox("Show Top N", [10, 20, 50, 100], index=1)
        
        # Filter data
        filtered_trends = trends_df[
            (trends_df['trend_score'] >= min_score) & 
            (trends_df['platform'].isin(selected_platforms))
        ].head(top_n)
        
        if not filtered_trends.empty:
            # Display trend cards
            for i in range(0, len(filtered_trends), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(filtered_trends):
                        trend_data = filtered_trends.iloc[i + j]
                        with col:
                            trend_card(trend_data)
            
            # Trend score distribution
            fig = px.histogram(
                filtered_trends, 
                x='trend_score', 
                nbins=20,
                title="Distribution of Trend Scores",
                labels={'trend_score': 'Trend Score (σ)', 'count': 'Number of Topics'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No trends match the selected criteria.")
    
    with tab2:
        st.subheader("Trend Analytics")
        
        if not timeseries_df.empty:
            # Time series chart
            fig = px.line(
                timeseries_df, 
                x='date', 
                y='post_count', 
                color='platform',
                title="Post Volume Over Time (30 Days)"
            )
            fig.update_layout(xaxis_title="Date", yaxis_title="Posts Count")
            st.plotly_chart(fig, use_container_width=True)
            
            # Growth rate vs trend score scatter
            if not trends_df.empty and 'growth_rate' in trends_df.columns:
                fig = px.scatter(
                    trends_df.head(50),
                    x='growth_rate',
                    y='trend_score',
                    size='current_count',
                    color='platform',
                    hover_data=['entity'],
                    title="Growth Rate vs Trend Score",
                    labels={
                        'growth_rate': 'Growth Rate (%)',
                        'trend_score': 'Trend Score (σ)'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Top entities by engagement
        if not trends_df.empty:
            st.subheader("Most Discussed Topics")
            top_engagement = trends_df.nlargest(10, 'current_count')[['entity', 'current_count', 'platform']]
            top_engagement.columns = ['Topic', 'Mentions', 'Platform']
            st.dataframe(top_engagement, hide_index=True)
    
    with tab3:
        st.subheader("Platform Analysis")
        
        if not trends_df.empty:
            # Platform distribution pie chart
            platform_stats = trends_df.groupby('platform').agg({
                'current_count': 'sum',
                'entity': 'count'
            }).reset_index()
            platform_stats.columns = ['Platform', 'Total Mentions', 'Unique Topics']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    platform_stats, 
                    values='Total Mentions', 
                    names='Platform',
                    title="Mentions by Platform"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.pie(
                    platform_stats, 
                    values='Unique Topics', 
                    names='Platform',
                    title="Unique Topics by Platform"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Platform comparison table
            st.subheader("Platform Comparison")
            platform_stats['Avg Mentions per Topic'] = (
                platform_stats['Total Mentions'] / platform_stats['Unique Topics']
            ).round(1)
            st.dataframe(platform_stats, hide_index=True)
    
    # Auto-refresh option
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Settings")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)")
    
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()
