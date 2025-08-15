import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

def show_quick_stats(engine):
    """Display quick stats about the system"""
    st.header("📊 Quick Stats", anchor=False)
    
    try:
        # Query total posts
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM posts"))
            total_posts = result.scalar()
            
            # Get platform stats
            platform_query = text("""
                SELECT platform, COUNT(*) as count 
                FROM posts 
                GROUP BY platform
            """)
            platform_df = pd.read_sql_query(platform_query, conn)
            
            # Get trend stats
            trend_query = text("""
                SELECT COUNT(*) as count, 
                       AVG(trend_score) as avg_score,
                       COUNT(CASE WHEN trend_score >= 2.0 THEN 1 END) as high_trends
                FROM trends 
                WHERE created_at >= datetime('now', '-24 hours')
            """)
            trend_df = pd.read_sql_query(trend_query, conn)
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Posts", f"{total_posts:,}")
            
        with col2:
            if not trend_df.empty:
                st.metric(
                    "Active Trends", 
                    int(trend_df['count'].iloc[0]),
                    delta=int(trend_df['high_trends'].iloc[0])
                )
            else:
                st.metric("Active Trends", "0")
                
        with col3:
            if not trend_df.empty and trend_df['avg_score'].iloc[0] is not None:
                st.metric(
                    "Avg Trend Score",
                    f"{trend_df['avg_score'].iloc[0]:.2f}σ"
                )
            else:
                st.metric("Avg Trend Score", "0.00σ")
        
        # Platform breakdown
        if not platform_df.empty:
            st.subheader("Platform Breakdown")
            st.dataframe(
                platform_df,
                column_config={
                    "platform": "Platform",
                    "count": st.column_config.NumberColumn(
                        "Post Count",
                        format="%d"
                    )
                },
                hide_index=True
            )
        
    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")
        st.error("Database might need initialization. Try running data ingestion first.")
