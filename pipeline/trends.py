import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text as sql
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict
import math
from database.schema import get_engine

class TrendAnalyzer:
    """Analyzes trending topics using statistical methods"""
    
    def __init__(self):
        self.engine = get_engine()
        self.min_count = int(os.getenv('TREND_MIN_COUNT', 10))
        self.window_hours = int(os.getenv('TREND_WINDOW_HOURS', 24))
        self.baseline_hours = int(os.getenv('TREND_BASELINE_HOURS', 168))  # 7 days
    
    def get_entity_counts(self, hours_back: int = 24) -> pd.DataFrame:
        """
        Get entity mention counts for the specified time period
        
        Args:
            hours_back: How many hours back to look
            
        Returns:
            DataFrame with entity counts
        """
        try:
            query = """
            SELECT 
                entities,
                platform,
                created_at,
                COUNT(*) as post_count
            FROM posts 
            WHERE datetime(created_at) > datetime('now', '-{} hours')
            AND entities IS NOT NULL
            AND entities != ''
            GROUP BY entities, platform, DATE(created_at)
            ORDER BY created_at DESC
            """.format(hours_back)
            
            df = pd.read_sql(query, self.engine)
            
            if df.empty:
                return pd.DataFrame()
            
            # Explode entities (they're stored as comma-separated)
            entity_rows = []
            for _, row in df.iterrows():
                entities = row['entities'].split(',')
                for entity in entities:
                    entity = entity.strip()
                    if entity:
                        entity_rows.append({
                            'entity': entity,
                            'platform': row['platform'],
                            'created_at': row['created_at'],
                            'post_count': row['post_count']
                        })
            
            if not entity_rows:
                return pd.DataFrame()
            
            entity_df = pd.DataFrame(entity_rows)
            entity_df['created_at'] = pd.to_datetime(entity_df['created_at'], format='mixed')
            
            return entity_df
            
        except Exception as e:
            logging.error(f"Error getting entity counts: {str(e)}")
            return pd.DataFrame()
    
    def calculate_trend_scores(self, current_hours: int = 24, baseline_hours: int = 168) -> pd.DataFrame:
        """
        Calculate trend scores using z-score analysis
        
        Args:
            current_hours: Current time window for trend calculation
            baseline_hours: Baseline period for comparison
            
        Returns:
            DataFrame with trend scores
        """
        try:
            # Get current period data
            current_df = self.get_entity_counts(current_hours)
            if current_df.empty:
                return pd.DataFrame()
            
            # Get baseline period data
            baseline_df = self.get_entity_counts(baseline_hours)
            if baseline_df.empty:
                return current_df  # Return current data without trend scores
            
            # Aggregate counts by entity and platform
            current_counts = current_df.groupby(['entity', 'platform'])['post_count'].sum().reset_index()
            current_counts.columns = ['entity', 'platform', 'current_count']
            
            baseline_counts = baseline_df.groupby(['entity', 'platform'])['post_count'].sum().reset_index()
            baseline_counts.columns = ['entity', 'platform', 'baseline_count']
            
            # Merge current and baseline
            merged = pd.merge(current_counts, baseline_counts, on=['entity', 'platform'], how='left')
            merged['baseline_count'] = merged['baseline_count'].fillna(0)
            
            # Filter entities with minimum current count
            merged = merged[merged['current_count'] >= self.min_count]
            
            if merged.empty:
                return pd.DataFrame()
            
            # Calculate statistics for trend scoring
            results = []
            
            for platform in merged['platform'].unique():
                platform_data = merged[merged['platform'] == platform]
                
                if len(platform_data) < 2:
                    continue
                
                # Calculate baseline statistics
                baseline_mean = platform_data['baseline_count'].mean()
                baseline_std = platform_data['baseline_count'].std()
                
                if baseline_std == 0:
                    baseline_std = 1  # Prevent division by zero
                
                for _, row in platform_data.iterrows():
                    entity = row['entity']
                    current_count = row['current_count']
                    baseline_count = row['baseline_count']
                    
                    # Z-score calculation
                    z_score = (current_count - baseline_mean) / baseline_std
                    
                    # Growth rate calculation
                    if baseline_count > 0:
                        growth_rate = (current_count - baseline_count) / baseline_count
                    else:
                        growth_rate = float('inf') if current_count > 0 else 0
                    
                    # Velocity (mentions per hour)
                    velocity = current_count / current_hours
                    
                    # Composite trend score
                    trend_score = z_score
                    
                    # Boost score for high growth rate
                    if growth_rate > 1.0:  # More than 100% growth
                        trend_score *= (1 + min(growth_rate, 5))  # Cap the boost
                    
                    # Boost score for high velocity
                    if velocity > baseline_mean / baseline_hours:
                        trend_score *= 1.2
                    
                    results.append({
                        'entity': entity,
                        'platform': platform,
                        'current_count': current_count,
                        'baseline_count': baseline_count,
                        'trend_score': trend_score,
                        'growth_rate': growth_rate,
                        'velocity': velocity,
                        'z_score': z_score,
                        'created_at': datetime.now()
                    })
            
            if not results:
                return pd.DataFrame()
            
            trend_df = pd.DataFrame(results)
            
            # Sort by trend score
            trend_df = trend_df.sort_values('trend_score', ascending=False)
            
            return trend_df
            
        except Exception as e:
            logging.error(f"Error calculating trend scores: {str(e)}")
            return pd.DataFrame()
    
    def detect_trending_topics(self, threshold: float = 2.0, top_k: int = 50) -> pd.DataFrame:
        """
        Detect trending topics above threshold
        
        Args:
            threshold: Minimum trend score threshold
            top_k: Maximum number of results to return
            
        Returns:
            DataFrame with trending topics
        """
        try:
            trend_df = self.calculate_trend_scores(self.window_hours, self.baseline_hours)
            
            if trend_df.empty:
                return pd.DataFrame()
            
            # Filter by threshold
            trending = trend_df[trend_df['trend_score'] >= threshold]
            
            # Take top K results
            trending = trending.head(top_k)
            
            return trending
            
        except Exception as e:
            logging.error(f"Error detecting trending topics: {str(e)}")
            return pd.DataFrame()
    
    def save_trends(self, trend_df: pd.DataFrame):
        """Save trend analysis results to database"""
        try:
            if trend_df.empty:
                return
            
            with self.engine.begin() as conn:
                # Create trends table if it doesn't exist
                conn.execute(sql("""
                    CREATE TABLE IF NOT EXISTS trends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        current_count INTEGER NOT NULL,
                        baseline_count INTEGER NOT NULL,
                        trend_score REAL NOT NULL,
                        growth_rate REAL NOT NULL,
                        velocity REAL NOT NULL,
                        z_score REAL NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        UNIQUE(entity, platform, created_at)
                    )
                """))
                
                # Insert trend data
                for _, row in trend_df.iterrows():
                    conn.execute(sql("""
                        INSERT OR REPLACE INTO trends 
                        (entity, platform, current_count, baseline_count, trend_score, 
                         growth_rate, velocity, z_score, created_at)
                        VALUES (:entity, :platform, :current_count, :baseline_count, 
                                :trend_score, :growth_rate, :velocity, :z_score, :created_at)
                    """), {
                        'entity': row['entity'],
                        'platform': row['platform'],
                        'current_count': int(row['current_count']),
                        'baseline_count': int(row['baseline_count']),
                        'trend_score': float(row['trend_score']),
                        'growth_rate': float(row['growth_rate']) if not math.isinf(row['growth_rate']) else 999.0,
                        'velocity': float(row['velocity']),
                        'z_score': float(row['z_score']),
                        'created_at': row['created_at'].isoformat()
                    })
            
            logging.info(f"Saved {len(trend_df)} trend records to database")
            
        except Exception as e:
            logging.error(f"Error saving trends: {str(e)}")
            raise
    
    def get_historical_trends(self, entity: str, days_back: int = 7) -> pd.DataFrame:
        """Get historical trend data for an entity"""
        try:
            query = """
            SELECT * FROM trends 
            WHERE entity = ? 
            AND datetime(created_at) > datetime('now', '-{} days')
            ORDER BY created_at DESC
            """.format(days_back)
            
            df = pd.read_sql(query, self.engine, params=[entity])
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            return df
            
        except Exception as e:
            logging.error(f"Error getting historical trends for {entity}: {str(e)}")
            return pd.DataFrame()
    
    def get_platform_trends(self, platform: str, limit: int = 20) -> pd.DataFrame:
        """Get trending topics for a specific platform"""
        try:
            query = """
            SELECT * FROM trends 
            WHERE platform = ? 
            AND datetime(created_at) > datetime('now', '-24 hours')
            ORDER BY trend_score DESC
            LIMIT ?
            """
            
            df = pd.read_sql(query, self.engine, params=[platform, limit])
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            return df
            
        except Exception as e:
            logging.error(f"Error getting platform trends for {platform}: {str(e)}")
            return pd.DataFrame()
    
    def detect_trend_changes(self, threshold_change: float = 1.0) -> pd.DataFrame:
        """Detect significant changes in trend scores"""
        try:
            # Get current trends
            current_trends = self.calculate_trend_scores(self.window_hours, self.baseline_hours)
            
            if current_trends.empty:
                return pd.DataFrame()
            
            # Get previous trends (24 hours ago)
            query = """
            SELECT entity, platform, trend_score as prev_score
            FROM trends 
            WHERE datetime(created_at) BETWEEN 
                  datetime('now', '-48 hours') AND datetime('now', '-24 hours')
            """
            
            prev_trends = pd.read_sql(query, self.engine)
            
            if prev_trends.empty:
                return current_trends  # No previous data to compare
            
            # Merge current and previous
            merged = pd.merge(
                current_trends[['entity', 'platform', 'trend_score', 'current_count']],
                prev_trends,
                on=['entity', 'platform'],
                how='left'
            )
            
            merged['prev_score'] = merged['prev_score'].fillna(0)
            merged['score_change'] = merged['trend_score'] - merged['prev_score']
            
            # Filter for significant changes
            significant_changes = merged[
                abs(merged['score_change']) >= threshold_change
            ].sort_values('score_change', ascending=False)
            
            return significant_changes
            
        except Exception as e:
            logging.error(f"Error detecting trend changes: {str(e)}")
            return pd.DataFrame()
    
    def get_trend_summary(self) -> Dict:
        """Get summary statistics of current trends"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_trends,
                AVG(trend_score) as avg_score,
                MAX(trend_score) as max_score,
                COUNT(CASE WHEN trend_score >= 2.0 THEN 1 END) as high_trends,
                COUNT(CASE WHEN trend_score >= 3.0 THEN 1 END) as viral_trends,
                COUNT(DISTINCT platform) as platforms
            FROM trends 
            WHERE datetime(created_at) > datetime('now', '-24 hours')
            """
            
            result = pd.read_sql(query, self.engine)
            
            if result.empty:
                return {}
            
            row = result.iloc[0]
            
            return {
                'total_trends': int(row['total_trends']),
                'avg_score': float(row['avg_score']) if row['avg_score'] else 0.0,
                'max_score': float(row['max_score']) if row['max_score'] else 0.0,
                'high_trends': int(row['high_trends']),
                'viral_trends': int(row['viral_trends']),
                'platforms': int(row['platforms']),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error getting trend summary: {str(e)}")
            return {}

def compute_trends(window_hours: int = 24, baseline_hours: int = 168, min_count: int = 10) -> pd.DataFrame:
    """
    Main function to compute trending topics
    
    Args:
        window_hours: Current time window
        baseline_hours: Baseline comparison period
        min_count: Minimum mentions required
        
    Returns:
        DataFrame with trending topics
    """
    try:
        analyzer = TrendAnalyzer()
        analyzer.min_count = min_count
        analyzer.window_hours = window_hours
        analyzer.baseline_hours = baseline_hours
        
        # Calculate trends
        trends = analyzer.calculate_trend_scores(window_hours, baseline_hours)
        
        if not trends.empty:
            # Save to database
            analyzer.save_trends(trends)
            
            logging.info(f"Computed {len(trends)} trending topics")
        else:
            logging.info("No trending topics found")
        
        return trends
        
    except Exception as e:
        logging.error(f"Error computing trends: {str(e)}")
        return pd.DataFrame()

def get_trending_topics(threshold: float = 2.0, limit: int = 50) -> pd.DataFrame:
    """Get current trending topics above threshold"""
    try:
        analyzer = TrendAnalyzer()
        return analyzer.detect_trending_topics(threshold, limit)
    except Exception as e:
        logging.error(f"Error getting trending topics: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run trend analysis
    trends = compute_trends()
    print(f"Found {len(trends)} trending topics")
    
    if not trends.empty:
        print("\nTop 10 trending topics:")
        top_trends = trends.head(10)
        for _, trend in top_trends.iterrows():
            print(f"  {trend['entity']} ({trend['platform']}): {trend['trend_score']:.2f}σ")
