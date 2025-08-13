import re
import logging
from typing import Dict, List, Set, Any
from collections import Counter
import string

class ContentFilter:
    """Content safety and quality filtering system"""
    
    def __init__(self):
        self.profanity_words = self._load_profanity_words()
        self.spam_patterns = self._compile_spam_patterns()
        self.hate_speech_indicators = self._load_hate_speech_indicators()
        self.misinformation_flags = self._load_misinformation_flags()
        
    def _load_profanity_words(self) -> Set[str]:
        """Load list of profanity words to filter"""
        # Basic profanity list - in production, you'd want a more comprehensive list
        return {
            'damn', 'hell', 'shit', 'fuck', 'fucking', 'bitch', 'bastard',
            'ass', 'asshole', 'crap', 'piss', 'cock', 'dick', 'pussy',
            'whore', 'slut', 'fag', 'faggot', 'nigga', 'nigger', 'retard',
            'gay', 'homo', 'dyke', 'tranny', 'chink', 'spic', 'wetback',
            'kike', 'gook', 'raghead', 'towelhead', 'sandnigger'
        }
    
    def _compile_spam_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for spam detection"""
        patterns = [
            r'(?i)\b(buy now|click here|free money|make money fast)\b',
            r'(?i)\b(viagra|cialis|weight loss|debt relief)\b',
            r'(?i)\b(nigerian prince|lottery winner|inheritance)\b',
            r'(?i)\b(crypto|bitcoin|investment opportunity)\b.*guaranteed',
            r'(?i)follow me @\w+',
            r'(?i)check out my (profile|link|website)',
            r'(?i)(subscribe|like and share|smash that button)',
            r'https?://\S+\.(tk|ml|ga|cf)/',  # Suspicious domains
            r'(?i)\b(download|install).*(app|software).*(free|now)\b',
            r'(?i)\b(limited time|act now|don\'t miss out)\b'
        ]
        
        return [re.compile(pattern) for pattern in patterns]
    
    def _load_hate_speech_indicators(self) -> Set[str]:
        """Load hate speech indicators"""
        return {
            'kill all', 'burn them', 'gas chamber', 'lynch', 'hang them',
            'subhuman', 'vermin', 'cancer', 'plague', 'disease',
            'go back to', 'send them back', 'deport them all',
            'white power', 'blood and soil', 'race war', 'final solution',
            'jews will not replace us', 'white genocide', 'great replacement',
            'based and redpilled', 'helicopter ride', 'day of the rope',
            'remove kebab', 'deus vult', '1488', '14 words'
        }
    
    def _load_misinformation_flags(self) -> List[str]:
        """Load misinformation flag patterns"""
        return [
            'fake news', 'hoax', 'conspiracy', 'deep state', 'false flag',
            'crisis actor', 'plandemic', 'scamdemic', 'sheeple',
            'wake up', 'do your research', 'mainstream media lies',
            'they don\'t want you to know', 'hidden truth', 'suppressed',
            'big pharma', 'big tech', 'globalist', 'illuminati',
            'new world order', 'agenda 21', 'population control'
        ]
    
    def check_profanity(self, text: str) -> Dict[str, Any]:
        """Check for profanity in text"""
        words = re.findall(r'\b\w+\b', text.lower())
        found_profanity = [word for word in words if word in self.profanity_words]
        
        return {
            'has_profanity': len(found_profanity) > 0,
            'profanity_count': len(found_profanity),
            'profanity_words': found_profanity[:5],  # Limit for privacy
            'severity': 'high' if len(found_profanity) > 3 else 'medium' if found_profanity else 'none'
        }
    
    def check_spam(self, text: str) -> Dict[str, Any]:
        """Check for spam patterns in text"""
        matches = []
        for pattern in self.spam_patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        
        # Additional spam indicators
        url_count = len(re.findall(r'https?://', text))
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        exclamation_count = text.count('!')
        
        spam_score = len(matches)
        if url_count > 2:
            spam_score += 1
        if caps_ratio > 0.3:
            spam_score += 1
        if exclamation_count > 5:
            spam_score += 1
        
        return {
            'is_spam': spam_score >= 2,
            'spam_score': spam_score,
            'spam_patterns': matches[:3],  # Limit for clarity
            'url_count': url_count,
            'caps_ratio': caps_ratio,
            'severity': 'high' if spam_score >= 3 else 'medium' if spam_score >= 1 else 'none'
        }
    
    def check_hate_speech(self, text: str) -> Dict[str, Any]:
        """Check for hate speech indicators"""
        text_lower = text.lower()
        found_indicators = []
        
        for indicator in self.hate_speech_indicators:
            if indicator in text_lower:
                found_indicators.append(indicator)
        
        # Check for slur variations and coded language
        coded_patterns = [
            r'\b13\s*%\b',  # Race-related statistics
            r'\b13\s*50\b',  # Crime statistics dogwhistle
            r'\b6\s*million\b',  # Holocaust denial
            r'\(((\(|\[)?\w+(\)|\])?)\)',  # Echo parentheses
        ]
        
        for pattern in coded_patterns:
            if re.search(pattern, text_lower):
                found_indicators.append(f"coded_language:{pattern}")
        
        severity = 'high' if len(found_indicators) >= 2 else 'medium' if found_indicators else 'none'
        
        return {
            'has_hate_speech': len(found_indicators) > 0,
            'hate_indicators': found_indicators[:3],  # Limit for privacy
            'severity': severity
        }
    
    def check_misinformation(self, text: str) -> Dict[str, Any]:
        """Check for misinformation indicators"""
        text_lower = text.lower()
        found_flags = []
        
        for flag in self.misinformation_flags:
            if flag in text_lower:
                found_flags.append(flag)
        
        # Check for conspiracy theory patterns
        conspiracy_patterns = [
            r'(?i)\b(they|them)\s+(control|want|don\'t want)',
            r'(?i)\b(cover.?up|hiding|suppressing)\b',
            r'(?i)\b(follow the money|cui bono)\b',
            r'(?i)\b(question everything|think for yourself)\b.*\b(sheep|sheeple)\b'
        ]
        
        pattern_matches = []
        for pattern in conspiracy_patterns:
            if re.search(pattern, text):
                pattern_matches.append('conspiracy_pattern')
        
        total_flags = len(found_flags) + len(pattern_matches)
        
        return {
            'has_misinformation_flags': total_flags > 0,
            'misinformation_count': total_flags,
            'flags_found': found_flags[:3],  # Limit for clarity
            'severity': 'high' if total_flags >= 3 else 'medium' if total_flags >= 1 else 'none'
        }
    
    def check_nsfw(self, text: str) -> Dict[str, Any]:
        """Check for NSFW (Not Safe For Work) content"""
        nsfw_words = {
            'sex', 'porn', 'nude', 'naked', 'orgasm', 'masturbate',
            'dildo', 'vibrator', 'bondage', 'bdsm', 'fetish',
            'strip', 'stripper', 'escort', 'prostitute', 'hooker',
            'onlyfans', 'premium snap', 'sugar daddy', 'sugar baby'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        found_nsfw = [word for word in words if word in nsfw_words]
        
        # Check for sexual content patterns
        sexual_patterns = [
            r'(?i)\b(send|show).*\b(nudes?|pics?)\b',
            r'(?i)\b(hook\s*up|netflix and chill)\b',
            r'(?i)\b(18\+|nsfw|not safe for work)\b',
            r'(?i)\b(xxx|adult content|mature)\b'
        ]
        
        pattern_matches = 0
        for pattern in sexual_patterns:
            if re.search(pattern, text):
                pattern_matches += 1
        
        nsfw_score = len(found_nsfw) + pattern_matches
        
        return {
            'is_nsfw': nsfw_score > 0,
            'nsfw_score': nsfw_score,
            'nsfw_words': found_nsfw[:3],  # Limit for privacy
            'severity': 'high' if nsfw_score >= 3 else 'medium' if nsfw_score >= 1 else 'none'
        }
    
    def check_quality(self, text: str) -> Dict[str, Any]:
        """Check content quality metrics"""
        if not text:
            return {'is_quality': False, 'score': 0, 'issues': ['empty_content']}
        
        issues = []
        score = 100  # Start with perfect score and deduct
        
        # Length checks
        if len(text) < 10:
            issues.append('too_short')
            score -= 30
        elif len(text) > 5000:
            issues.append('too_long')
            score -= 10
        
        # Character diversity
        char_types = {
            'letters': sum(c.isalpha() for c in text),
            'digits': sum(c.isdigit() for c in text),
            'spaces': sum(c.isspace() for c in text),
            'punctuation': sum(c in string.punctuation for c in text)
        }
        
        if char_types['letters'] / max(len(text), 1) < 0.5:
            issues.append('low_letter_ratio')
            score -= 20
        
        # Repetition check
        words = text.lower().split()
        if words:
            word_freq = Counter(words)
            most_common_ratio = word_freq.most_common(1)[0][1] / len(words)
            if most_common_ratio > 0.3:
                issues.append('repetitive')
                score -= 25
        
        # Caps check
        caps_ratio = sum(c.isupper() for c in text) / max(len(text), 1)
        if caps_ratio > 0.5:
            issues.append('excessive_caps')
            score -= 15
        
        # Sentence structure
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length < 3:
                issues.append('short_sentences')
                score -= 10
            elif avg_sentence_length > 50:
                issues.append('long_sentences')
                score -= 10
        
        return {
            'is_quality': score >= 60,
            'score': max(score, 0),
            'issues': issues,
            'char_stats': char_types,
            'word_count': len(words) if words else 0
        }
    
    def filter_content(self, text: str) -> Dict[str, Any]:
        """Comprehensive content filtering"""
        if not text:
            return {
                'is_safe': False,
                'overall_score': 0,
                'flags': ['empty_content'],
                'details': {}
            }
        
        # Run all checks
        checks = {
            'profanity': self.check_profanity(text),
            'spam': self.check_spam(text),
            'hate_speech': self.check_hate_speech(text),
            'misinformation': self.check_misinformation(text),
            'nsfw': self.check_nsfw(text),
            'quality': self.check_quality(text)
        }
        
        # Determine overall safety
        flags = []
        severity_scores = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
        total_severity = 0
        
        for check_name, result in checks.items():
            if check_name == 'quality':
                if not result['is_quality']:
                    flags.append('low_quality')
                continue
            
            # Check for safety violations
            is_violation = (
                result.get('has_profanity', False) or
                result.get('is_spam', False) or
                result.get('has_hate_speech', False) or
                result.get('has_misinformation_flags', False) or
                result.get('is_nsfw', False)
            )
            
            if is_violation:
                flags.append(check_name)
                total_severity += severity_scores.get(result.get('severity', 'medium'), 2)
        
        # Calculate overall score
        quality_score = checks['quality']['score']
        safety_penalty = min(total_severity * 15, 80)  # Cap penalty at 80
        overall_score = max(quality_score - safety_penalty, 0)
        
        # Determine if content is safe
        is_safe = overall_score >= 40 and total_severity < 6
        
        return {
            'is_safe': is_safe,
            'overall_score': overall_score,
            'flags': flags,
            'total_severity': total_severity,
            'details': checks,
            'recommendation': self._get_recommendation(flags, overall_score)
        }
    
    def _get_recommendation(self, flags: List[str], score: int) -> str:
        """Get content recommendation based on analysis"""
        if not flags and score >= 80:
            return 'approve'
        elif score >= 60 and len(flags) <= 1:
            return 'review'
        elif 'hate_speech' in flags or 'misinformation' in flags:
            return 'reject'
        elif score < 40:
            return 'reject'
        else:
            return 'review'
    
    def get_safe_excerpt(self, text: str, max_length: int = 200) -> str:
        """Get a safe excerpt of text for display"""
        # Filter out problematic content
        filter_result = self.filter_content(text)
        
        if not filter_result['is_safe'] and 'profanity' in filter_result['flags']:
            # Replace profanity with asterisks
            words = text.split()
            safe_words = []
            for word in words:
                clean_word = re.sub(r'[^\w]', '', word.lower())
                if clean_word in self.profanity_words:
                    safe_words.append('*' * len(word))
                else:
                    safe_words.append(word)
            text = ' '.join(safe_words)
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length-3] + '...'
        
        return text

# Global filter instance
_content_filter = None

def get_content_filter() -> ContentFilter:
    """Get or create global content filter instance"""
    global _content_filter
    if _content_filter is None:
        _content_filter = ContentFilter()
    return _content_filter

def filter_content(text: str) -> Dict[str, Any]:
    """Convenience function to filter content"""
    content_filter = get_content_filter()
    return content_filter.filter_content(text)

def is_content_safe(text: str) -> bool:
    """Quick check if content is safe"""
    result = filter_content(text)
    return result['is_safe']

def get_content_flags(text: str) -> List[str]:
    """Get list of content flags"""
    result = filter_content(text)
    return result['flags']

if __name__ == "__main__":
    # Test the content filter
    import argparse
    
    parser = argparse.ArgumentParser(description='Test content filter')
    parser.add_argument('text', help='Text to analyze')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    content_filter = ContentFilter()
    result = content_filter.filter_content(args.text)
    
    print(f"Text: {args.text}")
    print(f"Safe: {result['is_safe']}")
    print(f"Score: {result['overall_score']}")
    print(f"Flags: {', '.join(result['flags']) if result['flags'] else 'None'}")
    print(f"Recommendation: {result['recommendation']}")
    
    if args.verbose:
        print("\nDetailed Analysis:")
        for check_name, details in result['details'].items():
            print(f"  {check_name}: {details}")
