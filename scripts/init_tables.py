"""Initialize database tables"""
import os
import sys
import logging
from sqlalchemy import text

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from database.schema import Base, get_engine

def init_tables():
    """Initialize all database tables"""
    try:
        engine = get_engine()
        
        # Create all tables defined in the models
        Base.metadata.create_all(engine)
        
        # Verify tables were created
        with engine.connect() as conn:
            # Check posts table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"))
            if result.scalar():
                print("✅ Posts table created successfully")
            
            # Check trends table    
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='trends'"))
            if result.scalar():
                print("✅ Trends table created successfully")
            
            # Check alert_history table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alert_history'"))
            if result.scalar():
                print("✅ Alert history table created successfully")
        
        print("\n✨ Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    init_tables()
