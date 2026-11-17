import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "autoverse.db"

# LLM Configuration (Ollama)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Application Metadata
APP_NAME = "AutoVerse AI"
APP_TAGLINE = "Generative AI Powered Automotive Intelligence Platform"
APP_VERSION = "2.0.0"

# UI Theme Configuration
THEME = {
    "primary": "#00D2FF",
    "primary_glow": "rgba(0, 210, 255, 0.25)",
    "accent": "#FF3838",
    "background": "#0E1117",
    "card_bg": "#161B22",
    "border": "#30363D",
    "text_primary": "#F0F6FC",
    "text_muted": "#8B949E",
}

# Forbidden SQL Keywords for Read-Only Safety
FORBIDDEN_SQL_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", 
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "GRANT", "REVOKE", "COMMIT", "ROLLBACK", "EXEC", "EXECUTE"
]
