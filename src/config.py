"""Application Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    TESTING = os.getenv("TESTING", "False").lower() == "true"
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", 5000))

    # Feature flags
    ENABLE_CLINICAL_VALIDATION = os.getenv("ENABLE_CLINICAL_VALIDATION", "True").lower() == "true"
    ENABLE_HYPOTHESIS_GENERATION = os.getenv("ENABLE_HYPOTHESIS_GENERATION", "True").lower() == "true"

    # Analysis parameters
    EMOTION_INTENSITY_THRESHOLD = float(os.getenv("EMOTION_INTENSITY_THRESHOLD", 15.0))
    MIN_THEME_INSTANCES = int(os.getenv("MIN_THEME_INSTANCES", 3))
    DOMINANT_THEME_THRESHOLD = float(os.getenv("DOMINANT_THEME_THRESHOLD", 0.3))

config = Config()
