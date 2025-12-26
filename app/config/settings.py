"""
Application configuration settings
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma3-medical")

# Session storage
SESSION_DIR = BASE_DIR / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ==============================
# Clinical Safety Rules
# ==============================

# Minimum age for gynecology consultation
MIN_GYNECOLOGY_AGE = 12

# Pregnancy suspicion rules
PREGNANCY_RULES = {
    "min_months_since_lmp": 2,
    "required_symptoms": [
        "تهوع",
        "استفراغ",
        "خستگی",
        "ویار"
    ]
}


PREGNANCY_MODEL_NAME = "pregnancy-assistant"
