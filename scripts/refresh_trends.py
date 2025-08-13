#!/usr/bin/env python3
"""
Refresh trends analysis for the Social Media RAG system
This script computes trending topics and updates the trends database
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.trends import TrendAnalyzer, compute_trends
from alerts.notifier import get_notifier
from database.schema import get_engine
from utils.config import load_config
import pandas as pd

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_data_availability() -> dict:
    """Check if there's enough data to compute meaningful trends"""
    try:
        engine = get_engine()
        
        # Check total posts
        total_posts = pd.read_sql(
            "SELECT COUNT(*) as count FROM posts", 
            engine
        ).iloc[0]['count']
        
        # Check recent posts (last 24 hours)
        recent_posts = pd.read_sql(
            """
            SELECT COUNT(*) as count FROM posts 
            WHERE datetime(created_at) > datetime('now', '-24 hours')
            """, 
            engine
        ).iloc[0]['count']
        
        # Check posts with entities
        posts_with_entities = pd.read_sql(
            """
            SELECT COUNT(*) as count FROM posts 
            WHERE entities IS NOT NULL AND entities != ''
            """, 
            engine
        ).iloc[0]['count']
        
        # Check platform distribution
        platforms = pd.read_sql(
            "SELECT platform, COUNT(*) as count FROM posts GROUP BY platform", 
            engine
        )
        
        return {
            'total_posts': total_posts,
            'recent_posts': recent_posts,
            'posts_with_entities': posts_with_entities,
            'platforms': platforms.to_dict('records'),
            'sufficient_data': total_posts >= 50 and posts_with_entities >= 20
        }
        
    except Exception as e:
        logging.error(f"Error checking data availability: {str(e)}")
        return {
            'total_posts': 0,
            'recent_posts': 0,
            'posts_with_entities': 0,
            'platforms': [],
            'sufficient_data': False
        }

def run_trend_analysis(window_hours: int = 24, baseline_hours: int = 168, min_count: int = 10) -> dict:
    """Run complete trend analysis"""
    start_time = datetime.now()
    results = {
        'start_time': start_time,
        'trends_computed': 0,
        'high_trends': 0,
        'viral_trends': 0,
        'errors': [],
        'success': False
    }
    
    try:
        logging.info("Starting trend analysis...")
        
        # Initialize trend analyzer
        analyzer = TrendAnalyzer()
        analyzer.min_count = min_count
        analyzer.window_hours = window_hours
        analyzer.baseline_hours = baseline_hours
        
        # Compute trends
        trends_df = analyzer.calculate_trend_scores(window_hours, baseline_hours)
        
        if trends_df.empty:
            logging.warning("No trends computed - insufficient data or entities")
            results['errors'].append("No trends computed - insufficient data")
            return results
        
        # Save trends to database
        analyzer.save_trends(trends_df)
        
        # Count different trend levels
        high_trends = len(trends_df[trends_df['trend_score'] >= 2.0])
        viral_trends = len(trends_df[trends_df['trend_score'] >= 3.0])
        
        results.update({
            'trends_computed': len(trends_df),
            'high_trends': high_trends,
            'viral_trends': viral_trends,
            'success': True,
            'max_score': trends_df['trend_score'].max(),
            'avg_score': trends_df['trend_score'].mean()
        })
        
        logging.info(f"✅ Trend analysis completed:")
        logging.info(f"  - Total trends: {len(trends_df)}")
        logging.info(f"  - High trends (≥2σ): {high_trends}")
        logging.info(f"  - Viral trends (≥3σ): {viral_trends}")
        logging.info(f"  - Max score: {trends_df['trend_score'].max():.2f}σ")
        
        # Log top trends
        top_trends = trends_df.head(5)
        logging.info("Top 5 trending topics:")
        for _, trend in top_trends.iterrows():
            logging.info(f"  - {trend['entity']} ({trend['platform']}): {trend['trend_score']:.2f}σ")
        
        return results
        
    except Exception as e:
        error_msg = f"Error in trend analysis: {str(e)}"
        logging.error(error_msg)
        results['errors'].append(error_msg)
        return results
    
    finally:
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - start_time).total_seconds()

def check_for_alerts(threshold: float = 2.0) -> dict:
    """Check for trends that should trigger alerts"""
    alert_results = {
        'alerts_sent': 0,
        'alert_failures': 0,
        'trending_topics': []
    }
    
    try:
        # Load alert configuration
        config = load_config()
        
        # Get current high trends
        engine = get_engine()
        high_trends = pd.read_sql(f"""
            SELECT * FROM trends 
            WHERE trend_score >= {threshold}
            AND datetime(created_at) > datetime('now', '-1 hour')
            ORDER BY trend_score DESC
            LIMIT 10
        """, engine)
        
        if high_trends.empty:
            logging.info("No high trends found for alerts")
            return alert_results
        
        # Check if alerts are enabled
        try:
            with open('data/alert_config.json', 'r') as f:
                import json
                alert_config = json.load(f)
        except FileNotFoundError:
            alert_config = {'enabled': False}
        
        if not alert_config.get('enabled', False):
            logging.info("Alerts are disabled")
            return alert_results
        
        # Send alerts for qualifying trends
        notifier = get_notifier()
        
        for _, trend in high_trends.iterrows():
            trend_data = {
                'entity': trend['entity'],
                'platform': trend['platform'],
                'trend_score': trend['trend_score'],
                'current_count': trend['current_count'],
                'growth_rate': trend['growth_rate']
            }
            
            alert_results['trending_topics'].append(trend_data)
            
            # Determine alert type
            if trend['trend_score'] >= 3.0:
                alert_type = "viral_content"
            elif trend['trend_score'] >= 2.5:
                alert_type = "high_trend"
            else:
                alert_type = "moderate_trend"
            
            try:
                success = notifier.send_trend_alert(trend_data, alert_type)
                if success:
                    alert_results['alerts_sent'] += 1
                    logging.info(f"✅ Alert sent for {trend['entity']}")
                else:
                    alert_results['alert_failures'] += 1
                    logging.warning(f"⚠️ Failed to send alert for {trend['entity']}")
            
            except Exception as e:
                alert_results['alert_failures'] += 1
                logging.error(f"❌ Error sending alert for {trend['entity']}: {str(e)}")
        
        return alert_results
        
    except Exception as e:
        logging.error(f"Error checking for alerts: {str(e)}")
        return alert_results

def cleanup_old_trends(days_to_keep: int = 30):
    """Clean up old trend records to prevent database bloat"""
    try:
        engine = get_engine()
        
        # Count records before cleanup
        before_count = pd.read_sql("SELECT COUNT(*) as count FROM trends", engine).iloc[0]['count']
        
        # Delete old records
        with engine.begin() as conn:
            result = conn.execute(f"""
                DELETE FROM trends 
                WHERE datetime(created_at) < datetime('now', '-{days_to_keep} days')
            """)
            deleted_count = result.rowcount
        
        logging.info(f"🧹 Cleaned up {deleted_count} old trend records (kept {days_to_keep} days)")
        logging.info(f"   Records before: {before_count}, after: {before_count - deleted_count}")
        
    except Exception as e:
        logging.error(f"Error cleaning up old trends: {str(e)}")

def generate_trend_summary() -> dict:
    """Generate summary of current trending landscape"""
    try:
        analyzer = TrendAnalyzer()
        summary = analyzer.get_trend_summary()
        
        logging.info("📊 Current trend summary:")
        logging.info(f"  - Total trends: {summary.get('total_trends', 0)}")
        logging.info(f"  - Average score: {summary.get('avg_score', 0):.2f}σ")
        logging.info(f"  - Max score: {summary.get('max_score', 0):.2f}σ")
        logging.info(f"  - High trends: {summary.get('high_trends', 0)}")
        logging.info(f"  - Viral trends: {summary.get('viral_trends', 0)}")
        logging.info(f"  - Platforms: {summary.get('platforms', 0)}")
        
        return summary
        
    except Exception as e:
        logging.error(f"Error generating trend summary: {str(e)}")
        return {}

def main():
    """Main trend refresh function"""
    parser = argparse.ArgumentParser(description='Refresh trends analysis for Social Media RAG')
    parser.add_argument('--window-hours', type=int, default=24,
                       help='Hours for current trend window (default: 24)')
    parser.add_argument('--baseline-hours', type=int, default=168,
                       help='Hours for baseline comparison (default: 168)')
    parser.add_argument('--min-count', type=int, default=10,
                       help='Minimum mentions required for trending (default: 10)')
    parser.add_argument('--alert-threshold', type=float, default=2.0,
                       help='Trend score threshold for alerts (default: 2.0)')
    parser.add_argument('--skip-alerts', action='store_true',
                       help='Skip alert checking')
    parser.add_argument('--skip-cleanup', action='store_true',
                       help='Skip old data cleanup')
    parser.add_argument('--cleanup-days', type=int, default=30,
                       help='Days of trend data to keep (default: 30)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.verbose)
    logging.info("🔄 Starting trend refresh process")
    
    # Load configuration
    try:
        config = load_config()
        logging.info("✅ Configuration loaded")
    except Exception as e:
        logging.error(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)
    
    # Check data availability
    logging.info("📊 Checking data availability...")
    data_check = check_data_availability()
    
    if not data_check['sufficient_data']:
        logging.warning("⚠️ Insufficient data for meaningful trend analysis")
        logging.info(f"  - Total posts: {data_check['total_posts']}")
        logging.info(f"  - Posts with entities: {data_check['posts_with_entities']}")
        logging.info("  - Run data ingestion first: python pipeline/backfill_seed.py")
        sys.exit(1)
    
    logging.info(f"✅ Data check passed:")
    logging.info(f"  - Total posts: {data_check['total_posts']:,}")
    logging.info(f"  - Recent posts (24h): {data_check['recent_posts']:,}")
    logging.info(f"  - Posts with entities: {data_check['posts_with_entities']:,}")
    
    # Run trend analysis
    trend_results = run_trend_analysis(
        window_hours=args.window_hours,
        baseline_hours=args.baseline_hours,
        min_count=args.min_count
    )
    
    if not trend_results['success']:
        logging.error("❌ Trend analysis failed")
        for error in trend_results['errors']:
            logging.error(f"  - {error}")
        sys.exit(1)
    
    # Check for alerts
    if not args.skip_alerts:
        logging.info("🚨 Checking for alert conditions...")
        alert_results = check_for_alerts(args.alert_threshold)
        
        if alert_results['alerts_sent'] > 0:
            logging.info(f"✅ Sent {alert_results['alerts_sent']} alerts")
        
        if alert_results['alert_failures'] > 0:
            logging.warning(f"⚠️ Failed to send {alert_results['alert_failures']} alerts")
    
    # Cleanup old data
    if not args.skip_cleanup:
        logging.info("🧹 Cleaning up old trend data...")
        cleanup_old_trends(args.cleanup_days)
    
    # Generate summary
    summary = generate_trend_summary()
    
    # Final report
    print("\n" + "="*50)
    print("✅ TREND REFRESH COMPLETE")
    print("="*50)
    print(f"Trends computed: {trend_results['trends_computed']}")
    print(f"High trends (≥2σ): {trend_results['high_trends']}")
    print(f"Viral trends (≥3σ): {trend_results['viral_trends']}")
    print(f"Duration: {trend_results['duration']:.1f} seconds")
    
    if not args.skip_alerts:
        print(f"Alerts sent: {alert_results['alerts_sent']}")
        if alert_results['alert_failures'] > 0:
            print(f"Alert failures: {alert_results['alert_failures']}")
    
    print("\nNext steps:")
    print("1. View trends in dashboard: streamlit run app.py")
    print("2. Set up periodic refresh: crontab -e")
    print("3. Check alert configuration in web interface")

if __name__ == "__main__":
    main()
