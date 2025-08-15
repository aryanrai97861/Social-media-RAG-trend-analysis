"""Initialize database tables and indexes"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Base, get_engine
from sqlalchemy import text

def init_db():
    """Initialize database tables"""
    engine = get_engine()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create indexes for better query performance
    with engine.connect() as conn:
        # Index on posts created_at
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_posts_created_at 
            ON posts(created_at)
        """))
        
        # Index on posts platform
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_posts_platform 
            ON posts(platform)
        """))
        
        # Index on trends created_at
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trends_created_at 
            ON trends(created_at)
        """))
        
        conn.commit()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
