import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print Reddit-related environment variables
print("REDDIT_CLIENT_ID:", os.getenv("REDDIT_CLIENT_ID"))
print("REDDIT_CLIENT_SECRET:", os.getenv("REDDIT_CLIENT_SECRET"))
print("REDDIT_USER_AGENT:", os.getenv("REDDIT_USER_AGENT"))
