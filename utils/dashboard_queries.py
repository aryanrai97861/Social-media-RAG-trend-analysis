"""Database utility functions for dashboards"""
import pandas as pd
from sqlalchemy import text

def get_platform_stats(engine):
    """Get post counts by platform"""
    query = text("""
        SELECT platform, COUNT(*) as count 
        FROM posts 
        GROUP BY platform
    """)
    
    try:
        return pd.read_sql_query(query, engine)
    except Exception as e:
        print(f"Error getting platform stats: {str(e)}")
        return pd.DataFrame(columns=['platform', 'count'])

def get_trend_stats(engine):
    """Get trend statistics"""
    query = text("""
        SELECT platform, 
               COUNT(*) as trend_count,
               AVG(trend_score) as avg_score,
               MAX(trend_score) as max_score
        FROM trends
        GROUP BY platform
    """)
    
    try:
        return pd.read_sql_query(query, engine)
    except Exception as e:
        print(f"Error getting trend stats: {str(e)}")
        return pd.DataFrame(columns=['platform', 'trend_count', 'avg_score', 'max_score'])
