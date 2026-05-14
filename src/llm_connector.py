"""
LLM Connector - OpenRouter Edition (High Performance)
"""

import logging
import time
import httpx
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
    pass

class LLMConnector:
    def __init__(self) -> None:
        if not OPENROUTER_API_KEY:
            raise LLMConnectorError("OPENROUTER_API_KEY is missing!")
        
        # Tối ưu hóa: Sử dụng HTTPX client với timeout và pooling tùy chỉnh
        self.http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            http_client=self.http_client # Ép sử dụng pool kết nối
        )
        self.model_name = OPENROUTER_MODEL
        logger.info("LLMConnector: Initialized with Optimized Connection Pool")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        last_error: Optional[Exception] = None

        for attempt in range(1, API_MAX_RETRIES + 1):
            try:
                # Gọi API với các tham số tối giản
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=GEMINI_TEMPERATURE,
                    max_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                    # Bỏ bớt extra_headers nếu không cần thiết để giảm kích thước request
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                last_error = e
                if attempt < API_MAX_RETRIES:
                    time.sleep(API_RETRY_BACKOFF_BASE ** attempt)
                
        raise LLMConnectorError(f"API failed: {last_error}")
