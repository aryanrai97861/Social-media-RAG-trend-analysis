from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import re
import logging

@dataclass
class NormalizedPost:
    """Normalized social media post structure"""
    id: str
    platform: str  # reddit, rss, twitter, x
    author: Optional[str]
    text: str
    url: Optional[str]
    created_at: datetime
    hashtags: List[str]
    entities: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'platform': self.platform,
            'author': self.author or '',
            'text': self.text,
            'url': self.url or '',
            'created_at': self.created_at.isoformat(),
            'hashtags': ','.join(self.hashtags),
            'entities': ','.join(self.entities)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NormalizedPost':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            platform=data['platform'],
            author=data['author'] if data['author'] else None,
            text=data['text'],
            url=data['url'] if data['url'] else None,
            created_at=datetime.fromisoformat(data['created_at']),
            hashtags=data['hashtags'].split(',') if data['hashtags'] else [],
            entities=data['entities'].split(',') if data['entities'] else []
        )

class ContentNormalizer:
    """Handles content normalization and cleaning"""
    
    def __init__(self):
        self.hashtag_pattern = re.compile(r'#\w+', re.IGNORECASE)
        self.mention_pattern = re.compile(r'@\w+', re.IGNORECASE)
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove Reddit-specific formatting
        text = re.sub(r'\[removed\]|\[deleted\]', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text[:8000]  # Limit length
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        hashtags = self.hashtag_pattern.findall(text)
        return [tag.lower() for tag in hashtags]
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        mentions = self.mention_pattern.findall(text)
        return [mention.lower() for mention in mentions]
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        urls = self.url_pattern.findall(text)
        return urls
    
    def normalize_reddit_post(self, submission) -> Optional[NormalizedPost]:
        """Normalize Reddit submission to standard format"""
        try:
            # Combine title and selftext
            title = getattr(submission, 'title', '') or ''
            selftext = getattr(submission, 'selftext', '') or ''
            text = f"{title}\n\n{selftext}".strip()
            
            if not text or len(text) < 10:
                return None
            
            # Clean text
            clean_text = self.clean_text(text)
            
            # Extract features
            hashtags = self.extract_hashtags(clean_text)
            mentions = self.extract_mentions(clean_text)
            
            # Get author info
            author = None
            try:
                author = submission.author.name if submission.author else None
            except AttributeError:
                pass
            
            # Create normalized post
            return NormalizedPost(
                id=f"reddit_{submission.id}",
                platform="reddit",
                author=author,
                text=clean_text,
                url=f"https://reddit.com{submission.permalink}",
                created_at=datetime.fromtimestamp(submission.created_utc),
                hashtags=hashtags,
                entities=hashtags + mentions  # Simple entity extraction
            )
            
        except Exception as e:
            logging.error(f"Error normalizing Reddit post: {str(e)}")
            return None
    
    def normalize_rss_entry(self, entry, feed_url: str) -> Optional[NormalizedPost]:
        """Normalize RSS entry to standard format"""
        try:
            # Get title and summary/description
            title = getattr(entry, 'title', '') or ''
            summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
            text = f"{title}\n\n{summary}".strip()
            
            if not text or len(text) < 10:
                return None
            
            # Clean text
            clean_text = self.clean_text(text)
            
            # Extract features
            hashtags = self.extract_hashtags(clean_text)
            mentions = self.extract_mentions(clean_text)
            
            # Get publication date
            pub_date = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    import time
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                except (ValueError, TypeError):
                    pass
            
            # Generate unique ID
            entry_id = getattr(entry, 'id', '') or getattr(entry, 'link', '') or ''
            post_id = f"rss_{hash((entry_id, pub_date.isoformat()))}"
            
            return NormalizedPost(
                id=post_id,
                platform="rss",
                author=getattr(entry, 'author', None),
                text=clean_text,
                url=getattr(entry, 'link', ''),
                created_at=pub_date,
                hashtags=hashtags,
                entities=hashtags + mentions
            )
            
        except Exception as e:
            logging.error(f"Error normalizing RSS entry: {str(e)}")
            return None
    
    def normalize_twitter_post(self, tweet_data: dict) -> Optional[NormalizedPost]:
        """Normalize Twitter/X post to standard format"""
        try:
            text = tweet_data.get('text', '') or tweet_data.get('full_text', '')
            
            if not text or len(text) < 10:
                return None
            
            # Clean text
            clean_text = self.clean_text(text)
            
            # Extract features
            hashtags = self.extract_hashtags(clean_text)
            mentions = self.extract_mentions(clean_text)
            
            # Get creation time
            created_at = datetime.now()
            if 'created_at' in tweet_data:
                try:
                    from dateutil import parser
                    created_at = parser.parse(tweet_data['created_at'])
                except (ImportError, ValueError):
                    pass
            
            return NormalizedPost(
                id=f"twitter_{tweet_data.get('id_str', hash(text))}",
                platform="twitter",
                author=tweet_data.get('user', {}).get('screen_name'),
                text=clean_text,
                url=f"https://twitter.com/i/status/{tweet_data.get('id_str', '')}",
                created_at=created_at,
                hashtags=hashtags,
                entities=hashtags + mentions
            )
            
        except Exception as e:
            logging.error(f"Error normalizing Twitter post: {str(e)}")
            return None

# Global normalizer instance
_normalizer = None

def get_normalizer() -> ContentNormalizer:
    """Get or create global normalizer instance"""
    global _normalizer
    if _normalizer is None:
        _normalizer = ContentNormalizer()
    return _normalizer
