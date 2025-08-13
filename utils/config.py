import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json

class Config:
    """Configuration management for Social Media RAG system"""
    
    def __init__(self):
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables and files"""
        # Load from environment variables
        self._load_from_env()
        
        # Load from .env file if it exists
        self._load_from_env_file()
        
        # Set defaults
        self._set_defaults()
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_vars = {
            # Database
            'DB_PATH': os.getenv('DB_PATH'),
            'CHROMA_PATH': os.getenv('CHROMA_PATH'),
            
            # AI Models
            'EMBEDDING_MODEL': os.getenv('EMBEDDING_MODEL'),
            'GEN_MODEL': os.getenv('GEN_MODEL'),
            
            # Optional: OpenAI
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'OPENAI_EMBED_MODEL': os.getenv('OPENAI_EMBED_MODEL'),
            'OPENAI_GEN_MODEL': os.getenv('OPENAI_GEN_MODEL'),
            
            # Reddit API
            'REDDIT_CLIENT_ID': os.getenv('REDDIT_CLIENT_ID'),
            'REDDIT_CLIENT_SECRET': os.getenv('REDDIT_CLIENT_SECRET'),
            'REDDIT_USER_AGENT': os.getenv('REDDIT_USER_AGENT'),
            
            # RSS Feeds
            'RSS_FEEDS': os.getenv('RSS_FEEDS'),
            
            # Alerts
            'ALERT_WEBHOOK_URL': os.getenv('ALERT_WEBHOOK_URL'),
            'ALERT_EMAIL_SMTP': os.getenv('ALERT_EMAIL_SMTP'),
            'ALERT_EMAIL_USER': os.getenv('ALERT_EMAIL_USER'),
            'ALERT_EMAIL_PASS': os.getenv('ALERT_EMAIL_PASS'),
            'ALERT_EMAIL_TO': os.getenv('ALERT_EMAIL_TO'),
            
            # Trend Detection
            'TREND_MIN_COUNT': os.getenv('TREND_MIN_COUNT'),
            'TREND_WINDOW_HOURS': os.getenv('TREND_WINDOW_HOURS'),
            'TREND_BASELINE_HOURS': os.getenv('TREND_BASELINE_HOURS'),
        }
        
        # Only add non-None values
        self.config.update({k: v for k, v in env_vars.items() if v is not None})
    
    def _load_from_env_file(self):
        """Load configuration from .env file"""
        env_file = Path('.env')
        
        if not env_file.exists():
            logging.debug("No .env file found")
            return
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # Only set if not already in config (env vars take precedence)
                        if key not in self.config:
                            self.config[key] = value
            
            logging.debug("Configuration loaded from .env file")
            
        except Exception as e:
            logging.warning(f"Error loading .env file: {str(e)}")
    
    def _set_defaults(self):
        """Set default values for missing configuration"""
        defaults = {
            # Database
            'DB_PATH': './data/social.db',
            'CHROMA_PATH': './data/chroma',
            
            # AI Models
            'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
            'GEN_MODEL': 'google/flan-t5-base',
            
            # Reddit
            'REDDIT_USER_AGENT': 'social-rag-trends/1.0',
            
            # RSS Feeds (default feeds if none specified)
            'RSS_FEEDS': ','.join([
                'https://www.reddit.com/r/news/.rss',
                'https://www.reddit.com/r/technology/.rss',
                'https://www.reddit.com/r/worldnews/.rss'
            ]),
            
            # Alerts
            'ALERT_EMAIL_SMTP': 'smtp.gmail.com',
            
            # Trend Detection
            'TREND_MIN_COUNT': '10',
            'TREND_WINDOW_HOURS': '24',
            'TREND_BASELINE_HOURS': '168',
        }
        
        for key, default_value in defaults.items():
            if key not in self.config:
                self.config[key] = default_value
    
    def _validate_config(self):
        """Validate configuration values"""
        # Convert string numbers to integers
        int_keys = ['TREND_MIN_COUNT', 'TREND_WINDOW_HOURS', 'TREND_BASELINE_HOURS']
        for key in int_keys:
            if key in self.config:
                try:
                    self.config[key] = int(self.config[key])
                except ValueError:
                    logging.warning(f"Invalid integer value for {key}: {self.config[key]}")
                    # Use defaults
                    defaults = {
                        'TREND_MIN_COUNT': 10,
                        'TREND_WINDOW_HOURS': 24,
                        'TREND_BASELINE_HOURS': 168
                    }
                    self.config[key] = defaults[key]
        
        # Validate paths exist (create if needed)
        path_keys = ['DB_PATH', 'CHROMA_PATH']
        for key in path_keys:
            if key in self.config:
                path = Path(self.config[key])
                
                # Create parent directory if it doesn't exist
                path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate RSS feeds format
        if 'RSS_FEEDS' in self.config:
            feeds = self.config['RSS_FEEDS'].split(',')
            valid_feeds = []
            
            for feed in feeds:
                feed = feed.strip()
                if feed and (feed.startswith('http://') or feed.startswith('https://')):
                    valid_feeds.append(feed)
                elif feed:
                    logging.warning(f"Invalid RSS feed URL: {feed}")
            
            self.config['RSS_FEEDS'] = ','.join(valid_feeds)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def get_reddit_config(self) -> Dict[str, str]:
        """Get Reddit API configuration"""
        return {
            'client_id': self.get('REDDIT_CLIENT_ID'),
            'client_secret': self.get('REDDIT_CLIENT_SECRET'),
            'user_agent': self.get('REDDIT_USER_AGENT')
        }
    
    def get_email_config(self) -> Dict[str, str]:
        """Get email configuration"""
        return {
            'smtp_server': self.get('ALERT_EMAIL_SMTP'),
            'user': self.get('ALERT_EMAIL_USER'),
            'password': self.get('ALERT_EMAIL_PASS'),
            'to': self.get('ALERT_EMAIL_TO')
        }
    
    def get_trend_config(self) -> Dict[str, int]:
        """Get trend detection configuration"""
        return {
            'min_count': self.get('TREND_MIN_COUNT'),
            'window_hours': self.get('TREND_WINDOW_HOURS'),
            'baseline_hours': self.get('TREND_BASELINE_HOURS')
        }
    
    def get_rss_feeds(self) -> list:
        """Get list of RSS feed URLs"""
        feeds_str = self.get('RSS_FEEDS', '')
        if not feeds_str:
            return []
        
        return [feed.strip() for feed in feeds_str.split(',') if feed.strip()]
    
    def is_reddit_configured(self) -> bool:
        """Check if Reddit API is properly configured"""
        reddit_config = self.get_reddit_config()
        return bool(reddit_config['client_id'] and reddit_config['client_secret'])
    
    def is_email_configured(self) -> bool:
        """Check if email alerts are properly configured"""
        email_config = self.get_email_config()
        return bool(email_config['user'] and email_config['password'] and email_config['to'])
    
    def is_openai_configured(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.get('OPENAI_API_KEY'))
    
    def get_model_config(self) -> Dict[str, str]:
        """Get AI model configuration"""
        if self.is_openai_configured():
            return {
                'embedding_model': self.get('OPENAI_EMBED_MODEL', 'text-embedding-3-large'),
                'generation_model': self.get('OPENAI_GEN_MODEL', 'gpt-4o-mini'),
                'provider': 'openai'
            }
        else:
            return {
                'embedding_model': self.get('EMBEDDING_MODEL'),
                'generation_model': self.get('GEN_MODEL'),
                'provider': 'huggingface'
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self.config.copy()
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        try:
            with open(filepath, 'w') as f:
                # Don't save sensitive information
                safe_config = {k: v for k, v in self.config.items() 
                             if not any(sensitive in k.lower() for sensitive in 
                                      ['password', 'secret', 'key', 'token'])}
                json.dump(safe_config, f, indent=2)
            
            logging.info(f"Configuration saved to {filepath}")
            
        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status summary"""
        return {
            'reddit_configured': self.is_reddit_configured(),
            'email_configured': self.is_email_configured(),
            'openai_configured': self.is_openai_configured(),
            'rss_feeds_count': len(self.get_rss_feeds()),
            'database_path': self.get('DB_PATH'),
            'chroma_path': self.get('CHROMA_PATH'),
            'model_provider': self.get_model_config()['provider']
        }

# Global configuration instance
_config = None

def load_config() -> Config:
    """Load or get global configuration instance"""
    global _config
    
    if _config is None:
        _config = Config()
        logging.debug("Configuration loaded")
    
    return _config

def get_config_value(key: str, default: Any = None) -> Any:
    """Convenience function to get configuration value"""
    config = load_config()
    return config.get(key, default)

def reload_config():
    """Reload configuration from files"""
    global _config
    _config = None
    return load_config()

# Configuration validation functions
def validate_configuration() -> Dict[str, Any]:
    """Validate entire configuration and return status"""
    config = load_config()
    
    validation = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'status': config.get_status()
    }
    
    # Check required directories
    required_dirs = ['DB_PATH', 'CHROMA_PATH']
    for dir_key in required_dirs:
        path = Path(config.get(dir_key))
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                validation['errors'].append(f"Cannot create directory for {dir_key}: {str(e)}")
                validation['valid'] = False
    
    # Check model configuration
    model_config = config.get_model_config()
    if model_config['provider'] == 'openai' and not config.is_openai_configured():
        validation['warnings'].append("OpenAI models specified but API key not configured")
    
    # Check data sources
    if not config.is_reddit_configured() and not config.get_rss_feeds():
        validation['errors'].append("No data sources configured (Reddit or RSS feeds)")
        validation['valid'] = False
    
    # Check trend detection parameters
    trend_config = config.get_trend_config()
    if trend_config['window_hours'] >= trend_config['baseline_hours']:
        validation['warnings'].append("Trend window should be smaller than baseline period")
    
    return validation

if __name__ == "__main__":
    # Command-line interface for configuration management
    import argparse
    
    parser = argparse.ArgumentParser(description='Configuration management')
    parser.add_argument('--show', action='store_true', help='Show current configuration')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--status', action='store_true', help='Show configuration status')
    parser.add_argument('--save', type=str, help='Save configuration to file')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    config = load_config()
    
    if args.show:
        print("Current Configuration:")
        for key, value in config.to_dict().items():
            # Hide sensitive values
            if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key']):
                value = '***' if value else 'Not set'
            print(f"  {key}: {value}")
    
    elif args.validate:
        validation = validate_configuration()
        print(f"Configuration Valid: {validation['valid']}")
        
        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
    
    elif args.status:
        status = config.get_status()
        print("Configuration Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    elif args.save:
        config.save_to_file(args.save)
        print(f"Configuration saved to {args.save}")
    
    else:
        parser.print_help()
