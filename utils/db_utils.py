"""Database utilities for the application"""
from sqlalchemy import text
import pandas as pd
import logging

def get_quick_stats(engine):
    """Get quick statistics about posts and trends"""
    try:
        # Get post counts
        with engine.connect() as conn:
            post_count = conn.execute(text("SELECT COUNT(*) FROM posts")).scalar()
            
            # Get platform breakdown
            platform_stats = pd.read_sql_query(
                text("SELECT platform, COUNT(*) as count FROM posts GROUP BY platform"),
                conn
            )
            
            # Get trend stats
            trend_stats = pd.read_sql_query(
                text("""
                    SELECT COUNT(*) as count,
                           AVG(trend_score) as avg_score,
                           SUM(CASE WHEN trend_score >= 2 THEN 1 ELSE 0 END) as high_trends
                    FROM trends
                    WHERE created_at > datetime('now', '-24 hours')
                """),
                conn
            )
            
        return {
            'total_posts': post_count,
            'platform_stats': platform_stats,
            'trend_stats': trend_stats
        }
    except Exception as e:
        logging.error(f"Error getting quick stats: {str(e)}")
        return {
            'total_posts': 0,
            'platform_stats': pd.DataFrame(),
            'trend_stats': pd.DataFrame()
        }
