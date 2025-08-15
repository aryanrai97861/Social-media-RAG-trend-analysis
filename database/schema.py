import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text as sql
from datetime import datetime
import sqlite3

# Database configuration
DB_PATH = os.path.abspath(os.getenv('DB_PATH', './data/social.db'))

def get_engine():
    """Get SQLAlchemy engine instance"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    return engine

# Create Base class for ORM models
Base = declarative_base()

class Post(Base):
    """SQLAlchemy model for social media posts"""
    __tablename__ = 'posts'
    
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    author = Column(String)
    text = Column(Text, nullable=False)
    url = Column(String)
    created_at = Column(DateTime, nullable=False)
    hashtags = Column(Text)  # Comma-separated string
    entities = Column(Text)  # Comma-separated string
    indexed_at = Column(DateTime, default=datetime.utcnow)

class Trend(Base):
    """SQLAlchemy model for trend analysis results"""
    __tablename__ = 'trends'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    current_count = Column(Integer, nullable=False)
    baseline_count = Column(Integer, nullable=False)
    trend_score = Column(Float, nullable=False)
    growth_rate = Column(Float, nullable=False)
    velocity = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)

class AlertHistory(Base):
    """SQLAlchemy model for alert history"""
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    threshold_value = Column(Float)
    actual_value = Column(Float)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='active')

# Global engine instance
_engine = None
_SessionLocal = None

def get_engine():
    """Get or create database engine"""
    global _engine
    
    if _engine is None:
        # Ensure data directory exists
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Create engine with SQLite
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False}
        )
        
        logging.info(f"Database engine created for: {DB_PATH}")
    
    return _engine

def get_session():
    """Get database session"""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _SessionLocal()

def init_database():
    """Initialize database with all tables"""
    try:
        engine = get_engine()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create indexes for better performance
        with engine.connect() as conn:
            # Index on posts table
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)
            """))
            
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform)
            """))
            
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_posts_entities ON posts(entities)
            """))
            
            # Index on trends table
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_trends_entity ON trends(entity)
            """))
            
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_trends_created_at ON trends(created_at)
            """))
            
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_trends_score ON trends(trend_score)
            """))
            
            # Index on alert_history table
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alert_history(created_at)
            """))
            
            conn.execute(sql("""
                CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alert_history(entity)
            """))
            
            conn.commit()
        
        logging.info("Database initialized successfully with all tables and indexes")
        
        # Log database info
        with engine.connect() as conn:
            result = conn.execute(sql("SELECT COUNT(*) as count FROM posts")).fetchone()
            post_count = result[0] if result else 0
            
            result = conn.execute(sql("SELECT COUNT(*) as count FROM trends")).fetchone()
            trend_count = result[0] if result else 0
            
            logging.info(f"Database status: {post_count} posts, {trend_count} trends")
        
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        raise

def reset_database():
    """Reset database by dropping and recreating all tables"""
    try:
        engine = get_engine()
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logging.info("All tables dropped")
        
        # Recreate tables
        init_database()
        logging.info("Database reset completed")
        
    except Exception as e:
        logging.error(f"Error resetting database: {str(e)}")
        raise

def get_database_stats():
    """Get database statistics"""
    try:
        engine = get_engine()
        stats = {}
        
        with engine.connect() as conn:
            # Post statistics
            result = conn.execute(sql("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(DISTINCT platform) as platforms,
                    MIN(created_at) as oldest_post,
                    MAX(created_at) as newest_post
                FROM posts
            """)).fetchone()
            
            if result:
                stats['posts'] = {
                    'total': result[0],
                    'platforms': result[1],
                    'oldest': result[2],
                    'newest': result[3]
                }
            
            # Recent posts (last 24 hours)
            result = conn.execute(sql("""
                SELECT COUNT(*) as count FROM posts 
                WHERE datetime(created_at) > datetime('now', '-24 hours')
            """)).fetchone()
            
            stats['recent_posts'] = result[0] if result else 0
            
            # Platform breakdown
            platform_stats = conn.execute(sql("""
                SELECT platform, COUNT(*) as count 
                FROM posts 
                GROUP BY platform 
                ORDER BY count DESC
            """)).fetchall()
            
            stats['platform_breakdown'] = [
                {'platform': row[0], 'count': row[1]} 
                for row in platform_stats
            ]
            
            # Trend statistics
            result = conn.execute(sql("""
                SELECT 
                    COUNT(*) as total_trends,
                    AVG(trend_score) as avg_score,
                    MAX(trend_score) as max_score,
                    COUNT(CASE WHEN trend_score >= 2.0 THEN 1 END) as high_trends
                FROM trends
                WHERE datetime(created_at) > datetime('now', '-24 hours')
            """)).fetchone()
            
            if result:
                stats['trends'] = {
                    'total': result[0],
                    'avg_score': result[1] or 0,
                    'max_score': result[2] or 0,
                    'high_trends': result[3]
                }
            
            # Alert statistics
            result = conn.execute(sql("""
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_alerts
                FROM alert_history
                WHERE datetime(created_at) > datetime('now', '-7 days')
            """)).fetchone()
            
            if result:
                stats['alerts'] = {
                    'total_week': result[0],
                    'active': result[1]
                }
            
            # Database file size
            if os.path.exists(DB_PATH):
                stats['file_size_mb'] = os.path.getsize(DB_PATH) / (1024 * 1024)
            
            stats['last_updated'] = datetime.now().isoformat()
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting database stats: {str(e)}")
        return {'error': str(e)}

def vacuum_database():
    """Vacuum the database to reclaim space and optimize performance"""
    try:
        # Use direct SQLite connection for VACUUM
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")
        conn.close()
        
        logging.info("Database vacuum completed")
        
    except Exception as e:
        logging.error(f"Error vacuuming database: {str(e)}")
        raise

def backup_database(backup_path: str = None):
    """Create a backup of the database"""
    try:
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{DB_PATH}.backup_{timestamp}"
        
        # Ensure backup directory exists
        backup_dir = os.path.dirname(backup_path)
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
        
        # Use SQLite backup API
        source = sqlite3.connect(DB_PATH)
        backup = sqlite3.connect(backup_path)
        
        source.backup(backup)
        
        source.close()
        backup.close()
        
        logging.info(f"Database backed up to: {backup_path}")
        return backup_path
        
    except Exception as e:
        logging.error(f"Error backing up database: {str(e)}")
        raise

def check_database_health():
    """Check database health and integrity"""
    try:
        health_report = {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        engine = get_engine()
        
        with engine.connect() as conn:
            # Check database integrity
            try:
                result = conn.execute(sql("PRAGMA integrity_check")).fetchone()
                if result[0] != 'ok':
                    health_report['status'] = 'unhealthy'
                    health_report['issues'].append(f"Integrity check failed: {result[0]}")
            except Exception as e:
                health_report['issues'].append(f"Could not run integrity check: {str(e)}")
            
            # Check for missing indexes
            missing_indexes = []
            
            # Check if our custom indexes exist
            index_queries = [
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_posts_created_at'",
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_trends_score'"
            ]
            
            for query in index_queries:
                result = conn.execute(sql(query)).fetchone()
                if not result:
                    missing_indexes.append(query.split("'")[1])
            
            if missing_indexes:
                health_report['recommendations'].append(f"Missing indexes: {', '.join(missing_indexes)}")
            
            # Check for old data that could be archived
            old_data = conn.execute(sql("""
                SELECT COUNT(*) FROM trends 
                WHERE datetime(created_at) < datetime('now', '-90 days')
            """)).fetchone()
            
            if old_data and old_data[0] > 1000:
                health_report['recommendations'].append(f"Consider archiving {old_data[0]} old trend records")
            
            # Check database size
            if os.path.exists(DB_PATH):
                size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
                if size_mb > 100:  # If larger than 100MB
                    health_report['recommendations'].append(f"Database is {size_mb:.1f}MB, consider maintenance")
        
        # Overall health determination
        if health_report['issues']:
            health_report['status'] = 'needs_attention'
        elif health_report['recommendations']:
            health_report['status'] = 'healthy_with_recommendations'
        
        return health_report
        
    except Exception as e:
        return {
            'status': 'error',
            'issues': [f"Health check failed: {str(e)}"],
            'recommendations': []
        }

# Database maintenance functions
def cleanup_old_data(days_to_keep: int = 30):
    """Clean up old data to maintain database performance"""
    try:
        engine = get_engine()
        
        with engine.begin() as conn:
            # Clean old trends
            result = conn.execute(sql(f"""
                DELETE FROM trends 
                WHERE datetime(created_at) < datetime('now', '-{days_to_keep} days')
            """))
            trends_deleted = result.rowcount
            
            # Clean old alerts (keep more alert history)
            alert_days = days_to_keep * 2
            result = conn.execute(sql(f"""
                DELETE FROM alert_history 
                WHERE datetime(created_at) < datetime('now', '-{alert_days} days')
                AND status = 'resolved'
            """))
            alerts_deleted = result.rowcount
        
        logging.info(f"Cleanup completed: {trends_deleted} trends, {alerts_deleted} alerts deleted")
        
        return {
            'trends_deleted': trends_deleted,
            'alerts_deleted': alerts_deleted
        }
        
    except Exception as e:
        logging.error(f"Error during cleanup: {str(e)}")
        raise

if __name__ == "__main__":
    # Command-line interface for database operations
    import argparse
    
    parser = argparse.ArgumentParser(description='Database management operations')
    parser.add_argument('--init', action='store_true', help='Initialize database')
    parser.add_argument('--reset', action='store_true', help='Reset database (DANGER: deletes all data)')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--health', action='store_true', help='Check database health')
    parser.add_argument('--vacuum', action='store_true', help='Vacuum database')
    parser.add_argument('--backup', type=str, help='Backup database to specified path')
    parser.add_argument('--cleanup', type=int, help='Cleanup old data (specify days to keep)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.init:
        init_database()
        print("Database initialized")
    
    elif args.reset:
        confirm = input("This will delete ALL data. Type 'YES' to confirm: ")
        if confirm == 'YES':
            reset_database()
            print("Database reset completed")
        else:
            print("Reset cancelled")
    
    elif args.stats:
        stats = get_database_stats()
        print("Database Statistics:")
        print(f"Total posts: {stats.get('posts', {}).get('total', 0)}")
        print(f"Platforms: {stats.get('posts', {}).get('platforms', 0)}")
        print(f"Recent posts (24h): {stats.get('recent_posts', 0)}")
        print(f"Current trends: {stats.get('trends', {}).get('total', 0)}")
        if 'file_size_mb' in stats:
            print(f"Database size: {stats['file_size_mb']:.2f} MB")
    
    elif args.health:
        health = check_database_health()
        print(f"Database Status: {health['status']}")
        if health['issues']:
            print("Issues:")
            for issue in health['issues']:
                print(f"  - {issue}")
        if health['recommendations']:
            print("Recommendations:")
            for rec in health['recommendations']:
                print(f"  - {rec}")
    
    elif args.vacuum:
        vacuum_database()
        print("Database vacuum completed")
    
    elif args.backup:
        backup_path = backup_database(args.backup)
        print(f"Database backed up to: {backup_path}")
    
    elif args.cleanup:
        result = cleanup_old_data(args.cleanup)
        print(f"Cleanup completed: {result['trends_deleted']} trends, {result['alerts_deleted']} alerts deleted")
    
    else:
        parser.print_help()
