"""
Phase 2 LLM Engine - Centralized Configuration

Mọi cấu hình (API, model params, thresholds) tập trung tại đây.
KHÔNG hardcode magic numbers trong source code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_INPUT_DIR = BASE_DIR / "data" / "input"
DATA_OUTPUT_DIR = BASE_DIR / "data" / "output"
PROMPTS_DIR = BASE_DIR / "prompts"

# ============================================================
# OPENROUTER CONFIG (ONLY PROVIDER)
# ============================================================
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_SITE_URL: str = "https://hotel-pricing-ai.vercel.app"
OPENROUTER_SITE_NAME: str = "Hotel Pricing AI Advisor"

GEMINI_MAX_OUTPUT_TOKENS: int = 1024
GEMINI_TEMPERATURE: float = 0.3  # Thấp để giảm hallucination
GEMINI_TOP_P: float = 0.8

# ============================================================
# RETRY & RATE LIMITING
# ============================================================
API_MAX_RETRIES: int = 3
API_RETRY_BACKOFF_BASE: float = 2.0  # Exponential backoff: 2^n seconds
API_REQUESTS_PER_MINUTE: int = 12  # An toàn hơn cho Gemini Flash free tier

# ============================================================
# PROCESSING
# ============================================================
BATCH_SIZE: int = 10  # Số phòng xử lý mỗi batch
ONLY_RECOMMENDED: bool = True  # Chỉ generate advice cho is_recommended=1

# ============================================================
# VALIDATION (Anti-Hallucination)
# ============================================================
MAX_NUMBER_DEVIATION_PCT: float = 0.001  # Sai số cực thấp (0.1%) để ép AI dùng số chính xác
REQUIRED_ADVICE_FIELDS: list[str] = [
    "situation",
    "why",
    "action",
    "next_steps",
]

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
