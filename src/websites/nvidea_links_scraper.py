import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

# Get user agent from environment variables
USER_AGENT = os.getenv("USER_AGENT")
if not USER_AGENT:
    raise ValueError("USER_AGENT not found in environment variables")

HEADERS = {
    'User-Agent': USER_AGENT
}

# For testing
if __name__ == "__main__":
    print(f"Environment file path: {env_path}")
    print(f"Headers: {HEADERS}")