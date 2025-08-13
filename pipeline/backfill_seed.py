#!/usr/bin/env python3
"""
Backfill seed data for the social media RAG system
This script ingests initial data from Reddit and RSS feeds to populate the database
"""

import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import List
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingest_reddit import run as run_reddit_ingestion
from pipeline.ingest_rss import run as run_rss_ingestion
from pipeline.trends import compute_trends
from database.schema import init_database
from utils.config import load_config

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/backfill.log', mode='a')
        ]
    )

def run_data_ingestion(hours: int = 24, reddit_limit: int = 200, rss_limit: int = 50) -> dict:
    """
    Run data ingestion from multiple sources
    
    Args:
        hours: Number of hours of data to backfill (currently informational)
        reddit_limit: Number of posts per subreddit to ingest
        rss_limit: Number of entries per RSS feed to ingest
        
    Returns:
        Dictionary with ingestion results
    """
    results = {
        'reddit_posts': 0,
        'rss_entries': 0,
        'total_items': 0,
        'start_time': datetime.now(),
        'errors': []
    }
    
    try:
        logging.info(f"Starting data ingestion for ~{hours} hours of data")
        
        # Reddit ingestion
        logging.info("Starting Reddit ingestion...")
        try:
            reddit_count = run_reddit_ingestion(limit_per_sub=reddit_limit)
            results['reddit_posts'] = reddit_count
            logging.info(f"✅ Reddit ingestion completed: {reddit_count} posts")
        except Exception as e:
            error_msg = f"❌ Reddit ingestion failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
        
        # Brief pause between ingestions
        time.sleep(2)
        
        # RSS ingestion
        logging.info("Starting RSS ingestion...")
        try:
            rss_count = run_rss_ingestion(max_entries_per_feed=rss_limit)
            results['rss_entries'] = rss_count
            logging.info(f"✅ RSS ingestion completed: {rss_count} entries")
        except Exception as e:
            error_msg = f"❌ RSS ingestion failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
        
        results['total_items'] = results['reddit_posts'] + results['rss_entries']
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        logging.info(f"Data ingestion completed: {results['total_items']} total items in {results['duration']:.1f}s")
        
        return results
        
    except Exception as e:
        error_msg = f"Critical error in data ingestion: {str(e)}"
        logging.error(error_msg)
        results['errors'].append(error_msg)
        return results

def run_trend_computation():
    """Run initial trend computation on ingested data"""
    try:
        logging.info("Starting trend computation...")
        
        trends_df = compute_trends(
            window_hours=24,
            baseline_hours=168,  # 7 days
            min_count=5  # Lower threshold for initial computation
        )
        
        if not trends_df.empty:
            trend_count = len(trends_df)
            top_trends = trends_df.head(5)
            
            logging.info(f"✅ Trend computation completed: {trend_count} trends identified")
            logging.info("Top 5 trending topics:")
            for _, trend in top_trends.iterrows():
                logging.info(f"  - {trend['entity']} ({trend['platform']}): {trend['trend_score']:.2f}σ")
        else:
            logging.warning("⚠️  No trends computed - may need more data")
        
        return len(trends_df) if not trends_df.empty else 0
        
    except Exception as e:
        logging.error(f"❌ Trend computation failed: {str(e)}")
        return 0

def validate_environment():
    """Validate that required environment variables are set"""
    required_vars = ['DB_PATH', 'CHROMA_PATH']
    optional_vars = ['REDDIT_CLIENT_ID', 'RSS_FEEDS']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        logging.error(f"❌ Missing required environment variables: {missing_required}")
        return False
    
    if missing_optional:
        logging.warning(f"⚠️  Missing optional environment variables: {missing_optional}")
        logging.warning("Some features may be limited")
    
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        'data',
        'data/chroma',
        'context/wikipedia_cache',
        'logs'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logging.debug(f"✅ Directory ensured: {directory}")
        except Exception as e:
            logging.error(f"❌ Failed to create directory {directory}: {str(e)}")
            return False
    
    return True

def main():
    """Main backfill function"""
    parser = argparse.ArgumentParser(description='Backfill seed data for Social Media RAG system')
    parser.add_argument('--hours', type=int, default=24, 
                       help='Hours of data to backfill (default: 24)')
    parser.add_argument('--reddit-limit', type=int, default=200,
                       help='Posts per subreddit to ingest (default: 200)')
    parser.add_argument('--rss-limit', type=int, default=50,
                       help='Entries per RSS feed to ingest (default: 50)')
    parser.add_argument('--skip-trends', action='store_true',
                       help='Skip trend computation step')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--force', action='store_true',
                       help='Force backfill even if data exists')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.verbose)
    logging.info("🚀 Starting Social Media RAG backfill process")
    
    # Validate environment
    if not validate_environment():
        logging.error("❌ Environment validation failed")
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        logging.error("❌ Directory creation failed")
        sys.exit(1)
    
    # Load configuration
    try:
        config = load_config()
        logging.info("✅ Configuration loaded successfully")
    except Exception as e:
        logging.error(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)
    
    # Initialize database
    try:
        init_database()
        logging.info("✅ Database initialized successfully")
    except Exception as e:
        logging.error(f"❌ Database initialization failed: {str(e)}")
        sys.exit(1)
    
    # Check if data already exists (unless force flag is used)
    if not args.force:
        try:
            from database.schema import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute("SELECT COUNT(*) as count FROM posts").fetchone()
                existing_posts = result[0] if result else 0
                
                if existing_posts > 100:  # Arbitrary threshold
                    response = input(f"Found {existing_posts} existing posts. Continue anyway? (y/N): ")
                    if response.lower() != 'y':
                        logging.info("Backfill cancelled by user")
                        sys.exit(0)
        except Exception as e:
            logging.warning(f"Could not check existing data: {str(e)}")
    
    # Run data ingestion
    ingestion_results = run_data_ingestion(
        hours=args.hours,
        reddit_limit=args.reddit_limit,
        rss_limit=args.rss_limit
    )
    
    # Display ingestion results
    print("\n" + "="*50)
    print("📊 INGESTION RESULTS")
    print("="*50)
    print(f"Reddit Posts: {ingestion_results['reddit_posts']:,}")
    print(f"RSS Entries: {ingestion_results['rss_entries']:,}")
    print(f"Total Items: {ingestion_results['total_items']:,}")
    print(f"Duration: {ingestion_results.get('duration', 0):.1f} seconds")
    
    if ingestion_results['errors']:
        print(f"\n⚠️  Errors encountered:")
        for error in ingestion_results['errors']:
            print(f"  - {error}")
    
    # Run trend computation if not skipped
    if not args.skip_trends:
        print("\n" + "="*50)
        print("📈 TREND COMPUTATION")
        print("="*50)
        
        if ingestion_results['total_items'] > 0:
            trend_count = run_trend_computation()
            print(f"Trends Computed: {trend_count}")
        else:
            print("⚠️  Skipping trend computation - no data ingested")
    
    # Final summary
    print("\n" + "="*50)
    print("✅ BACKFILL COMPLETE")
    print("="*50)
    print("Next steps:")
    print("1. Run the Streamlit app: streamlit run app.py")
    print("2. Set up periodic ingestion: bash scripts/run_ingestion.sh")
    print("3. Configure alerts in the web interface")
    print("4. Index additional context: python scripts/index_context.py")

if __name__ == "__main__":
    main()
