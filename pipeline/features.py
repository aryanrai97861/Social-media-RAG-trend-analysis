import re
import string
from collections import Counter
from typing import List, Dict, Set
import logging

# Regex patterns for feature extraction
HASHTAG_PATTERN = re.compile(r'(?i)#[a-z0-9_]+')
MENTION_PATTERN = re.compile(r'(?i)@[a-z0-9_]+')
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
WORD_PATTERN = re.compile(r'(?i)\b[a-z][a-z0-9_\']*\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# Common stop words
STOP_WORDS = set([
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
    'have', 'had', 'what', 'said', 'each', 'which', 'their', 'time',
    'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some',
    'her', 'would', 'make', 'like', 'into', 'him', 'has', 'two',
    'more', 'very', 'after', 'words', 'its', 'just', 'where', 'most',
    'now', 'people', 'my', 'made', 'over', 'did', 'down', 'only', 'way',
    'find', 'use', 'may', 'water', 'long', 'little', 'get', 'through',
    'back', 'much', 'before', 'go', 'good', 'new', 'write', 'our',
    'used', 'me', 'man', 'too', 'any', 'day', 'same', 'right', 'look',
    'think', 'also', 'around', 'another', 'came', 'come', 'work',
    'three', 'must', 'because', 'does', 'part', 'even', 'place',
    'well', 'such', 'here', 'take', 'why', 'help', 'put', 'different',
    'away", "turn", "want", "every", "don\'t", "should", "never",
    'year', 'still', 'public', 'read', 'know', 'large', 'available',
    'end', 'become', 'member', 'please', 'including', 'old', 'see',
    'however', 'given', 'both', 'important', 'though', 'information',
    'nothing', 'those', 'business', 'home', 'mr', 'ms', 'dr', 'could',
    'would', 'should', 'might', 'need', 'want', 'going', 'doing',
    'reddit', 'post', 'comment', 'submission', 'thread', 'op', 'edit',
    'deleted', 'removed'
])

# Internet slang and abbreviations
INTERNET_SLANG = {
    'lol': 'laugh_out_loud',
    'lmao': 'laughing_my_ass_off',
    'rofl': 'rolling_on_floor_laughing',
    'omg': 'oh_my_god',
    'wtf': 'what_the_f',
    'fml': 'f_my_life',
    'tbh': 'to_be_honest',
    'imo': 'in_my_opinion',
    'imho': 'in_my_humble_opinion',
    'afaik': 'as_far_as_i_know',
    'irl': 'in_real_life',
    'tl;dr': 'too_long_didnt_read',
    'tldr': 'too_long_didnt_read',
    'eli5': 'explain_like_im_5',
    'ama': 'ask_me_anything',
    'til': 'today_i_learned',
    'ysk': 'you_should_know',
    'psa': 'public_service_announcement'
}

def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words, removing stop words and normalizing
    
    Args:
        text: Input text to tokenize
        
    Returns:
        List of normalized tokens
    """
    if not text:
        return []
    
    # Convert to lowercase and find words
    words = WORD_PATTERN.findall(text.lower())
    
    # Filter out stop words and short words
    tokens = []
    for word in words:
        if len(word) >= 3 and word not in STOP_WORDS:
            # Normalize internet slang
            normalized_word = INTERNET_SLANG.get(word, word)
            tokens.append(normalized_word)
    
    return tokens

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    hashtags = HASHTAG_PATTERN.findall(text)
    return [tag.lower() for tag in hashtags]

def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from text"""
    mentions = MENTION_PATTERN.findall(text)
    return [mention.lower() for mention in mentions]

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    urls = URL_PATTERN.findall(text)
    return urls

def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text"""
    emails = EMAIL_PATTERN.findall(text)
    return [email.lower() for email in emails]

def extract_keywords(text: str, top_k: int = 10) -> List[tuple]:
    """
    Extract top keywords from text based on frequency
    
    Args:
        text: Input text
        top_k: Number of top keywords to return
        
    Returns:
        List of (keyword, frequency) tuples
    """
    tokens = tokenize(text)
    
    if not tokens:
        return []
    
    # Count word frequencies
    word_freq = Counter(tokens)
    
    # Return top k keywords
    return word_freq.most_common(top_k)

def extract_entities(text: str) -> List[str]:
    """
    Extract entities from text (hashtags, mentions, keywords)
    
    Args:
        text: Input text
        
    Returns:
        List of extracted entities
    """
    if not text:
        return []
    
    try:
        entities = set()
        
        # Extract hashtags (without #)
        hashtags = extract_hashtags(text)
        entities.update([tag[1:] for tag in hashtags if len(tag) > 1])
        
        # Extract mentions (without @)
        mentions = extract_mentions(text)
        entities.update([mention[1:] for mention in mentions if len(mention) > 1])
        
        # Extract top keywords
        keywords = extract_keywords(text, top_k=5)
        entities.update([keyword for keyword, freq in keywords if freq >= 2])
        
        # Look for potential trending topics or named entities
        # Simple patterns for common entities
        entity_patterns = {
            'covid': r'(?i)\b(covid|coronavirus|pandemic|vaccine|pfizer|moderna|omicron|delta)\b',
            'climate': r'(?i)\b(climate|global warming|greenhouse|carbon|emission|greta)\b',
            'crypto': r'(?i)\b(bitcoin|crypto|blockchain|ethereum|nft|dogecoin|elon)\b',
            'politics': r'(?i)\b(trump|biden|election|democrat|republican|congress|senate)\b',
            'tech': r'(?i)\b(apple|google|microsoft|amazon|meta|twitter|tiktok|ai|chatgpt)\b',
            'sports': r'(?i)\b(nfl|nba|fifa|olympics|superbowl|worldcup|playoff)\b',
            'entertainment': r'(?i)\b(netflix|disney|marvel|starwars|game of thrones|stranger things)\b'
        }
        
        for category, pattern in entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                entities.update([match.lower() for match in matches])
        
        # Clean and filter entities
        cleaned_entities = []
        for entity in entities:
            entity = entity.strip().lower()
            if (len(entity) >= 3 and 
                entity not in STOP_WORDS and 
                not entity.isdigit() and
                entity.isalnum()):
                cleaned_entities.append(entity)
        
        return sorted(list(set(cleaned_entities)))
        
    except Exception as e:
        logging.error(f"Error extracting entities: {str(e)}")
        return []

def extract_sentiment_indicators(text: str) -> Dict[str, int]:
    """
    Extract basic sentiment indicators from text
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with positive, negative, and neutral indicators
    """
    if not text:
        return {'positive': 0, 'negative': 0, 'neutral': 0}
    
    # Simple sentiment word lists
    positive_words = {
        'good', 'great', 'excellent', 'amazing', 'awesome', 'fantastic',
        'love', 'like', 'enjoy', 'happy', 'pleased', 'satisfied',
        'wonderful', 'brilliant', 'perfect', 'best', 'favorite',
        'thank', 'thanks', 'grateful', 'appreciate', 'nice',
        'cool', 'sweet', 'dope', 'fire', 'lit', 'poggers',
        'based', 'wholesome', 'blessed'
    }
    
    negative_words = {
        'bad', 'terrible', 'awful', 'horrible', 'disgusting',
        'hate', 'dislike', 'angry', 'mad', 'furious', 'annoyed',
        'sad', 'depressed', 'disappointed', 'frustrated',
        'worst', 'suck', 'sucks', 'stupid', 'dumb', 'idiotic',
        'cringe', 'toxic', 'trash', 'garbage', 'pathetic',
        'fail', 'failure', 'disaster', 'nightmare'
    }
    
    text_lower = text.lower()
    words = set(tokenize(text))
    
    positive_count = len(words & positive_words)
    negative_count = len(words & negative_words)
    
    # Count exclamation marks and caps as intensity indicators
    exclamation_count = text.count('!')
    caps_words = len([word for word in text.split() if word.isupper() and len(word) > 2])
    
    return {
        'positive': positive_count + (exclamation_count // 2),
        'negative': negative_count + (caps_words // 2),
        'neutral': max(0, len(words) - positive_count - negative_count),
        'exclamation_count': exclamation_count,
        'caps_words': caps_words
    }

def extract_trending_patterns(text: str) -> Dict[str, List[str]]:
    """
    Extract patterns that might indicate trending content
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with different types of trending patterns
    """
    patterns = {
        'breaking_news': [],
        'viral_phrases': [],
        'meme_references': [],
        'event_markers': []
    }
    
    try:
        text_lower = text.lower()
        
        # Breaking news indicators
        breaking_patterns = [
            r'(?i)\bbreaking\b.*\bnews\b',
            r'(?i)\bjust\s+in\b',
            r'(?i)\burgent\b',
            r'(?i)\balert\b',
            r'(?i)\bupdate\b'
        ]
        
        for pattern in breaking_patterns:
            matches = re.findall(pattern, text)
            patterns['breaking_news'].extend(matches)
        
        # Viral phrase indicators
        viral_patterns = [
            r'(?i)\bgone\s+viral\b',
            r'(?i)\btrending\b',
            r'(?i)\bgoing\s+viral\b',
            r'(?i)\beveryone\s+is\s+talking\b',
            r'(?i)\binternet\s+is\s+losing\b'
        ]
        
        for pattern in viral_patterns:
            matches = re.findall(pattern, text)
            patterns['viral_phrases'].extend(matches)
        
        # Meme references
        meme_indicators = [
            'stonks', 'hodl', 'diamond hands', 'to the moon',
            'this is fine', 'change my mind', 'ok boomer',
            'big chungus', 'among us', 'sus', 'impostor',
            'chad', 'karen', 'simp', 'based', 'cringe',
            'poggers', 'kekw', 'monke', 'bonk'
        ]
        
        for indicator in meme_indicators:
            if indicator in text_lower:
                patterns['meme_references'].append(indicator)
        
        # Event markers
        event_patterns = [
            r'(?i)\b(today|yesterday|now|just|recently|currently)\b',
            r'(?i)\b(happening|occurred|announced|revealed|confirmed)\b',
            r'(?i)\b(live|real\s+time|as\s+we\s+speak)\b'
        ]
        
        for pattern in event_patterns:
            matches = re.findall(pattern, text)
            patterns['event_markers'].extend(matches)
    
    except Exception as e:
        logging.error(f"Error extracting trending patterns: {str(e)}")
    
    return patterns

def calculate_engagement_score(text: str) -> float:
    """
    Calculate a simple engagement score based on text features
    
    Args:
        text: Input text
        
    Returns:
        Engagement score (0.0 to 1.0)
    """
    if not text:
        return 0.0
    
    try:
        score = 0.0
        
        # Length score (optimal around 100-300 characters)
        length = len(text)
        if 50 <= length <= 500:
            score += 0.2
        elif length > 500:
            score += 0.1
        
        # Hashtag presence
        hashtags = extract_hashtags(text)
        if hashtags:
            score += min(len(hashtags) * 0.1, 0.3)
        
        # Question marks (encourage engagement)
        question_count = text.count('?')
        score += min(question_count * 0.1, 0.2)
        
        # Sentiment indicators
        sentiment = extract_sentiment_indicators(text)
        if sentiment['positive'] > sentiment['negative']:
            score += 0.1
        
        # Trending patterns
        patterns = extract_trending_patterns(text)
        pattern_count = sum(len(v) for v in patterns.values())
        score += min(pattern_count * 0.05, 0.2)
        
        return min(score, 1.0)
        
    except Exception as e:
        logging.error(f"Error calculating engagement score: {str(e)}")
        return 0.0

def extract_all_features(text: str) -> Dict:
    """
    Extract comprehensive features from text
    
    Args:
        text: Input text
        
    Returns:
        Dictionary containing all extracted features
    """
    try:
        return {
            'entities': extract_entities(text),
            'hashtags': extract_hashtags(text),
            'mentions': extract_mentions(text),
            'urls': extract_urls(text),
            'keywords': extract_keywords(text),
            'sentiment': extract_sentiment_indicators(text),
            'trending_patterns': extract_trending_patterns(text),
            'engagement_score': calculate_engagement_score(text),
            'word_count': len(tokenize(text)),
            'char_count': len(text)
        }
    except Exception as e:
        logging.error(f"Error extracting features: {str(e)}")
        return {}
