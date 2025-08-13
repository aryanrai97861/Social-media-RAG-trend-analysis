import os
import feedparser
import time
from datetime import datetime, timezone
from sqlalchemy import create_engine, text as sql
from typing import List, Optional
import logging
from .normalize import get_normalizer, NormalizedPost
from .features import extract_entities
from database.schema import get_engine

class RSSIngester:
    """Handles RSS feed content ingestion"""
    
    def __init__(self):
        self.normalizer = get_normalizer()
        self.engine = get_engine()
        self.feeds = self._load_feed_urls()
    
    def _load_feed_urls(self) -> List[str]:
        """Load RSS feed URLs from environment"""
        feeds_env = os.getenv("RSS_FEEDS", "")
        if not feeds_env:
            return self._get_default_feeds()
        
        feeds = [url.strip() for url in feeds_env.split(',') if url.strip()]
        return feeds
    
    def _get_default_feeds(self) -> List[str]:
        """Get default RSS feeds if none configured"""
        return [
            "https://www.reddit.com/r/news/.rss",
            "https://www.reddit.com/r/technology/.rss",
            "https://www.reddit.com/r/worldnews/.rss",
            "https://feeds.bbci.co.uk/news/rss.xml",
            "http://rss.cnn.com/rss/edition.rss",
            "https://techcrunch.com/feed/",
            "https://www.wired.com/feed/rss",
            "https://feeds.reuters.com/reuters/topNews"
        ]
    
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
    
    def ingest_feed(self, feed_url: str, max_entries: int = 50) -> int:
        """
        Ingest entries from a single RSS feed
        
        Args:
            feed_url: URL of the RSS feed
            max_entries: Maximum number of entries to process
            
        Returns:
            Number of entries successfully ingested
        """
        try:
            logging.info(f"Fetching feed: {feed_url}")
            
            # Parse feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logging.warning(f"Feed parsing issues for {feed_url}: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logging.warning(f"No entries found in feed: {feed_url}")
                return 0
            
            ingested_count = 0
            entries = feed.entries[:max_entries]  # Limit entries processed
            
            for entry in entries:
                try:
                    # Normalize entry
                    normalized_post = self.normalizer.normalize_rss_entry(entry, feed_url)
                    
                    if normalized_post:
                        # Extract entities
                        entities = extract_entities(normalized_post.text)
                        normalized_post.entities = entities
                        
                        # Save to database
                        self.save_post(normalized_post)
                        ingested_count += 1
                
                except Exception as e:
                    logging.error(f"Error processing RSS entry: {str(e)}")
                    continue
            
            logging.info(f"Ingested {ingested_count} entries from {feed_url}")
            return ingested_count
            
        except Exception as e:
            logging.error(f"Error ingesting RSS feed {feed_url}: {str(e)}")
            return 0
    
    def ingest_all_feeds(self, max_entries_per_feed: int = 50) -> int:
        """Ingest from all configured RSS feeds"""
        total_ingested = 0
        
        for feed_url in self.feeds:
            try:
                count = self.ingest_feed(feed_url, max_entries_per_feed)
                total_ingested += count
                
                # Rate limiting between feeds
                time.sleep(1.0)
                
            except Exception as e:
                logging.error(f"Error processing feed {feed_url}: {str(e)}")
                continue
        
        return total_ingested
    
    def validate_feed(self, feed_url: str) -> dict:
        """Validate an RSS feed URL"""
        try:
            feed = feedparser.parse(feed_url)
            
            return {
                'valid': not feed.bozo,
                'title': getattr(feed.feed, 'title', 'Unknown'),
                'description': getattr(feed.feed, 'description', ''),
                'entries_count': len(feed.entries) if hasattr(feed, 'entries') else 0,
                'last_updated': getattr(feed.feed, 'updated', ''),
                'error': str(feed.bozo_exception) if feed.bozo else None
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'title': '',
                'description': '',
                'entries_count': 0,
                'last_updated': ''
            }
    
    def get_feed_info(self) -> List[dict]:
        """Get information about all configured feeds"""
        feed_info = []
        
        for feed_url in self.feeds:
            info = self.validate_feed(feed_url)
            info['url'] = feed_url
            feed_info.append(info)
        
        return feed_info
    
    def add_feed(self, feed_url: str) -> bool:
        """Add a new RSS feed URL"""
        try:
            # Validate feed first
            validation = self.validate_feed(feed_url)
            
            if not validation['valid']:
                logging.error(f"Invalid RSS feed: {feed_url} - {validation['error']}")
                return False
            
            if feed_url not in self.feeds:
                self.feeds.append(feed_url)
                logging.info(f"Added RSS feed: {feed_url}")
                return True
            else:
                logging.info(f"RSS feed already exists: {feed_url}")
                return True
                
        except Exception as e:
            logging.error(f"Error adding RSS feed {feed_url}: {str(e)}")
            return False
    
    def remove_feed(self, feed_url: str) -> bool:
        """Remove an RSS feed URL"""
        try:
            if feed_url in self.feeds:
                self.feeds.remove(feed_url)
                logging.info(f"Removed RSS feed: {feed_url}")
                return True
            else:
                logging.warning(f"RSS feed not found: {feed_url}")
                return False
                
        except Exception as e:
            logging.error(f"Error removing RSS feed {feed_url}: {str(e)}")
            return False

def run(max_entries_per_feed: int = 50) -> int:
    """
    Main function to run RSS ingestion
    
    Args:
        max_entries_per_feed: Maximum entries per feed
        
    Returns:
        Total number of entries ingested
    """
    try:
        ingester = RSSIngester()
        
        logging.info(f"Starting RSS ingestion from {len(ingester.feeds)} feeds")
        total_ingested = ingester.ingest_all_feeds(max_entries_per_feed)
        
        logging.info(f"RSS ingestion completed. Total entries: {total_ingested}")
        return total_ingested
        
    except Exception as e:
        logging.error(f"Error in RSS ingestion: {str(e)}")
        return 0

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run ingestion
    result = run()
    print(f"Ingested {result} entries from RSS feeds")
