"""
Configuration loader.
Reads environment variables from .env file.
Will be expanded in Brief 1.2 with actual config values.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Config values will be added in Brief 1.2
