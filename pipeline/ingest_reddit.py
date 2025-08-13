import os
import time
import praw
from datetime import datetime, timezone
from sqlalchemy import create_engine, text as sql
from typing import List, Optional
import logging
from .normalize import get_normalizer, NormalizedPost
from .features import extract_entities
from database.schema import get_engine

class RedditIngester:
    """Handles Reddit content ingestion"""
    
    def __init__(self):
        self.reddit = None
        self.normalizer = get_normalizer()
        self.engine = get_engine()
        self._initialize_reddit()
    
    def _initialize_reddit(self):
        """Initialize Reddit API client"""
        try:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "social-rag-trends/1.0")
            
            if not client_id or not client_secret:
                logging.warning("Reddit credentials not found. Reddit ingestion disabled.")
                return
            
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            
            # Test connection
            self.reddit.user.me()
            logging.info("Reddit API initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing Reddit API: {str(e)}")
            self.reddit = None
    
    def save_post(self, post: NormalizedPost):
        """Save normalized post to database"""
        try:
            with self.engine.begin() as conn:
                # Ensure posts table exists
                conn.execute(sql("""
                    CREATE TABLE IF NOT EXISTS posts (
                        id TEXT PRIMARY KEY,
                        platform TEXT NOT NULL,
                        author TEXT,
                        text TEXT NOT NULL,
                        url TEXT,
                        created_at TIMESTAMP NOT NULL,
                        hashtags TEXT,
                        entities TEXT,
                        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Insert or replace post
                conn.execute(sql("""
                    INSERT OR REPLACE INTO posts 
                    (id, platform, author, text, url, created_at, hashtags, entities)
                    VALUES (:id, :platform, :author, :text, :url, :created_at, :hashtags, :entities)
                """), post.to_dict())
                
        except Exception as e:
            logging.error(f"Error saving post {post.id}: {str(e)}")
            raise
    
    def ingest_subreddit(self, subreddit_name: str, limit: int = 100, sort_type: str = "new") -> int:
        """
        Ingest posts from a specific subreddit
        
        Args:
            subreddit_name: Name of the subreddit
            limit: Maximum number of posts to fetch
            sort_type: Sort type ('new', 'hot', 'top')
            
        Returns:
            Number of posts successfully ingested
        """
        if not self.reddit:
            logging.warning("Reddit API not available")
            return 0
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            ingested_count = 0
            
            # Get submissions based on sort type
            if sort_type == "new":
                submissions = subreddit.new(limit=limit)
            elif sort_type == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort_type == "top":
                submissions = subreddit.top(limit=limit, time_filter="day")
            else:
                submissions = subreddit.new(limit=limit)
            
            for submission in submissions:
                try:
                    # Normalize submission
                    normalized_post = self.normalizer.normalize_reddit_post(submission)
                    
                    if normalized_post:
                        # Extract entities
                        entities = extract_entities(normalized_post.text)
                        normalized_post.entities = entities
                        
                        # Save to database
                        self.save_post(normalized_post)
                        ingested_count += 1
                        
                        # Rate limiting
                        time.sleep(0.1)
                    
                except Exception as e:
                    logging.error(f"Error processing submission {submission.id}: {str(e)}")
                    continue
            
            logging.info(f"Ingested {ingested_count} posts from r/{subreddit_name}")
            return ingested_count
            
        except Exception as e:
            logging.error(f"Error ingesting from r/{subreddit_name}: {str(e)}")
            return 0
    
    def ingest_multiple_subreddits(self, subreddits: List[str], limit_per_sub: int = 100) -> int:
        """Ingest from multiple subreddits"""
        total_ingested = 0
        
        for subreddit in subreddits:
            count = self.ingest_subreddit(subreddit, limit=limit_per_sub)
            total_ingested += count
            
            # Longer delay between subreddits
            time.sleep(1.0)
        
        return total_ingested
    
    def get_trending_subreddits(self, limit: int = 10) -> List[str]:
        """Get list of trending subreddits"""
        try:
            if not self.reddit:
                return []
            
            trending = []
            for subreddit in self.reddit.subreddits.popular(limit=limit):
                trending.append(subreddit.display_name)
            
            return trending
            
        except Exception as e:
            logging.error(f"Error getting trending subreddits: {str(e)}")
            return []

# Default subreddits to monitor
DEFAULT_SUBREDDITS = [
    "news",
    "technology", 
    "worldnews",
    "memes",
    "TodayILearned",
    "AskReddit",
    "funny",
    "politics",
    "science",
    "entertainment"
]

def run(limit_per_sub: int = 200, subreddits: Optional[List[str]] = None) -> int:
    """
    Main function to run Reddit ingestion
    
    Args:
        limit_per_sub: Number of posts per subreddit
        subreddits: List of subreddits (uses default if None)
        
    Returns:
        Total number of posts ingested
    """
    try:
        ingester = RedditIngester()
        
        if subreddits is None:
            subreddits = DEFAULT_SUBREDDITS
        
        logging.info(f"Starting Reddit ingestion from {len(subreddits)} subreddits")
        total_ingested = ingester.ingest_multiple_subreddits(subreddits, limit_per_sub)
        
        logging.info(f"Reddit ingestion completed. Total posts: {total_ingested}")
        return total_ingested
        
    except Exception as e:
        logging.error(f"Error in Reddit ingestion: {str(e)}")
        return 0

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run ingestion
    result = run()
    print(f"Ingested {result} posts from Reddit")
