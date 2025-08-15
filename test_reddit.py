import praw
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_reddit_connection():
    try:
        # Get credentials from environment
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")
        
        print("Initializing Reddit client with:")
        print(f"Client ID: {client_id}")
        print(f"User Agent: {user_agent}")
        
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        # Test connection by getting some posts
        print("\nTesting connection by fetching posts from r/news...")
        for submission in reddit.subreddit("news").hot(limit=1):
            print(f"Successfully fetched post: {submission.title}")
            
        print("\nReddit connection successful!")
        
    except Exception as e:
        print(f"\nError connecting to Reddit: {str(e)}")

if __name__ == "__main__":
    test_reddit_connection()
