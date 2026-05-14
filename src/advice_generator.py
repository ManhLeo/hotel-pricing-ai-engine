"""
Advice Generator - Layer 3: Main Orchestrator (Super-Lite API Version)
"""

import json
import logging
from typing import Any, Optional

from src.prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from src.context_builder import RoomContext
from src.llm_connector import LLMConnector, LLMConnectorError
from src.validator import AdviceValidator

logger = logging.getLogger(__name__)


class AdviceGenerator:
    """Orchestrator tối ưu hóa cho tốc độ phản hồi cực cao."""

    def __init__(self, connector: Optional[LLMConnector] = None) -> None:
        """Khởi tạo và Pre-render các thành phần tĩnh."""
        self.connector = connector or LLMConnector()
        self.system_prompt = SYSTEM_PROMPT
        
        # Pre-render few-shot examples để không phải xử lý JSON.dumps mỗi request
        self._pre_rendered_examples = self._pre_render_examples(FEW_SHOT_EXAMPLES)
        logger.info("AdviceGenerator: Static components pre-rendered.")

    @staticmethod
    def _pre_render_examples(examples: list) -> str:
        if not examples:
            return ""
        parts = ["=== EXAMPLES ==="]
        for i, ex in enumerate(examples, 1):
            parts.append(f"\n--- Example {i} ---\nInput:\n{ex.get('input', '')}")
            # Pre-dump JSON output
            output_str = json.dumps(ex.get("output", {}), ensure_ascii=False, indent=2)
            parts.append(f"Output:\n{output_str}")
        parts.append("\n=== END EXAMPLES ===\n")
        return "\n".join(parts)

    def _build_user_prompt(self, context: RoomContext) -> str:
        """Xây dựng user prompt bằng cách nối các khối đã pre-render."""
        # Grounding data (Xử lý động cho từng phòng)
        valid_numbers = context.get_all_numeric_values()
        numbers_registry = ", ".join(map(str, sorted(valid_numbers)))

        # Nối chuỗi cực nhanh bằng list join
        return "\n".join([
            self._pre_rendered_examples,
            "=== INPUT DATA ===",
            context.to_prompt_text(),
            "\n=== VALID NUMBERS REGISTRY (GROUND TRUTH) ===",
            f"The ONLY numbers permitted: {numbers_registry}",
            "\n=== INSTRUCTIONS ===",
            "Analyze data and return PURE JSON (situation, why, action, next_steps).",
            "Professional English. ZERO Hallucination."
        ])

    def generate_single(
        self, context: RoomContext
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Luồng thực thi thẳng (Straight-line execution)."""
        user_prompt = self._build_user_prompt(context)

        try:
            raw_response = self.connector.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
            # Validate và trả về ngay
            return AdviceValidator.validate(raw_response, context)
        except LLMConnectorError as e:
            return None, [str(e)]
