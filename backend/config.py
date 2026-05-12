"""Configuration settings for the application"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings"""

    # API Configuration
    API_TITLE = "CS-GWYNT TCG"
    API_VERSION = "0.1.0"

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tcg.db")

    # Server Configuration
    DEBUG = os.getenv("DEBUG", "False") == "True"

    # Game Configuration
    MAX_HAND_SIZE = 10
    MAX_DECK_SIZE = 40
    MIN_DECK_SIZE = 25


settings = Settings()
