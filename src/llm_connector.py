"""
LLM Connector - OpenRouter Edition
Trách nhiệm: Gửi prompt tới OpenRouter API (OpenAI Compatible).
"""

import logging
import time
from typing import Optional
from openai import OpenAI


from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_BASE_URL,
    OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_TEMPERATURE,
    API_MAX_RETRIES,
    API_RETRY_BACKOFF_BASE,
)

logger = logging.getLogger(__name__)

class LLMConnectorError(Exception):
    """Custom exception cho các lỗi liên quan đến LLM API."""
    pass

class LLMConnector:
    """Quản lý kết nối và giao tiếp với OpenRouter API."""

    def __init__(self) -> None:
        """Khởi tạo OpenAI client cho OpenRouter."""
        if not OPENROUTER_API_KEY:
            raise LLMConnectorError(
                "OPENROUTER_API_KEY is missing! "
                "Please add it to your environment variables or .env file."
            )
        
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        self.model_name = OPENROUTER_MODEL
        logger.info("LLMConnector: Initialized with OpenRouter model %s", self.model_name)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Gửi prompt tới OpenRouter và trả về text response."""
        last_error: Optional[Exception] = None

        for attempt in range(1, API_MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": OPENROUTER_SITE_URL,
                        "X-Title": OPENROUTER_SITE_NAME,
                    },
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=GEMINI_TEMPERATURE,
                    max_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                )
                text = response.choices[0].message.content.strip()
                logger.info("API response received from OpenRouter (%d chars)", len(text))
                return text

            except Exception as e:
                last_error = e
                wait_time = API_RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "OpenRouter call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt, API_MAX_RETRIES, str(e), wait_time
                )
                time.sleep(wait_time)

        raise LLMConnectorError(
            f"OpenRouter API failed after {API_MAX_RETRIES} retries. Last error: {last_error}"
        )
