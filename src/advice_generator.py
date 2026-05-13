"""
Advice Generator - Layer 3: Main Orchestrator

Trách nhiệm: Điều phối toàn bộ flow:
  ContextBuilder → Prompt Assembly → LLMConnector → Validator → Output

Đây là module DUY NHẤT biết về tất cả các layer khác.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from config.settings import (
    API_REQUESTS_PER_MINUTE,
    BATCH_SIZE,
    ONLY_RECOMMENDED,
    PROMPTS_DIR,
)
from src.context_builder import ContextBuilder, RoomContext
from src.llm_connector import LLMConnector, LLMConnectorError
from src.validator import AdviceValidator

logger = logging.getLogger(__name__)


class AdviceGenerator:
    """Orchestrator chính cho Phase 2 LLM Engine.

    Flow xử lý:
    1. Load system prompt + few-shot examples
    2. Đọc CSV → List[RoomContext]
    3. Filter (chỉ phòng cần advice)
    4. Với mỗi phòng: build prompt → call LLM → validate → save
    """

    def __init__(self, connector: Optional[LLMConnector] = None) -> None:
        """Khởi tạo generator.

        Args:
            connector: LLMConnector instance. Nếu None, tạo mới.
        """
        self.connector = connector or LLMConnector()
        self.system_prompt = self._load_system_prompt()
        self.few_shot_examples = self._load_few_shot_examples()
        logger.info("AdviceGenerator initialized")

    @staticmethod
    def _load_system_prompt() -> str:
        """Đọc system prompt từ file.

        Returns:
            Nội dung system prompt.
        """
        prompt_path = PROMPTS_DIR / "system_prompt.md"
        if not prompt_path.exists():
            logger.warning("System prompt not found at %s, using default", prompt_path)
            return "You are a Senior Revenue Manager."

        text = prompt_path.read_text(encoding="utf-8")
        logger.info("Loaded system prompt (%d chars)", len(text))
        return text

    @staticmethod
    def _load_few_shot_examples() -> list[dict[str, Any]]:
        """Đọc few-shot examples từ file JSON.

        Returns:
            Danh sách ví dụ mẫu.
        """
        examples_path = PROMPTS_DIR / "few_shot_examples.json"
        if not examples_path.exists():
            logger.warning("Few-shot examples not found at %s", examples_path)
            return []

        with open(examples_path, "r", encoding="utf-8") as f:
            examples = json.load(f)

        logger.info("Loaded %d few-shot examples", len(examples))
        return examples

    def _build_user_prompt(self, context: RoomContext) -> str:
        """Xây dựng user prompt từ RoomContext.

        Kết hợp: few-shot examples + room data + output instruction.

        Args:
            context: RoomContext của phòng cần xử lý.

        Returns:
            User prompt hoàn chỉnh.
        """
        parts: list[str] = []

        # Few-shot examples
        if self.few_shot_examples:
            parts.append("=== VÍ DỤ ===")
            for i, ex in enumerate(self.few_shot_examples, 1):
                parts.append(f"\n--- Ví dụ {i} ---")
                parts.append(f"Input:\n{ex.get('input', '')}")
                parts.append(f"Output:\n{json.dumps(ex.get('output', {}), ensure_ascii=False, indent=2)}")
            parts.append("\n=== HẾT VÍ DỤ ===\n")

        # Room data
        # Extract all numeric values to create a "Truth Registry"
        valid_numbers = context.get_all_numeric_values()
        numbers_registry = ", ".join([str(n) for n in sorted(list(valid_numbers))])

        parts.append("=== INPUT DATA ===")
        parts.append(context.to_prompt_text())
        
        parts.append("\n=== VALID NUMBERS REGISTRY (GROUND TRUTH) ===")
        parts.append(f"The ONLY numbers you are permitted to use are: {numbers_registry}")
        parts.append("Using any other numbers will be considered a failure.")
        parts.append("Using only English language.")

        # Output instruction
        parts.append("\n=== INSTRUCTIONS ===")
        parts.append(
            "Analyze the room data provided above and return a JSON object with 4 fields:\n"
            '- "situation": Summarize the current status of the room.\n'
            '- "why": Explain the rationale using the exact metrics from the registry.\n'
            '- "action": Propose the specific action linked to the provided label.\n'
            '- "next_steps": Forecast the expected results.\n\n'
            "CRITICAL CONSTRAINTS:\n"
            "- USE EXACT NUMBERS: Do not round 12.8% to 13%. Use '12.8%'.\n"
            "- ZERO HALLUCINATION: If a number is not in the REGISTRY above, DO NOT USE IT.\n"
            "- PROFESSIONAL TONE: Write as a Senior Revenue Manager.\n"
            "- FORMAT: Return PURE JSON only (no markdown blocks)."
        )

        return "\n".join(parts)

    def _should_process(self, context: RoomContext) -> bool:
        """Kiểm tra phòng có cần generate advice không.

        Args:
            context: RoomContext cần kiểm tra.

        Returns:
            True nếu cần xử lý.
        """
        if ONLY_RECOMMENDED and not context.is_recommended:
            return False

        return context.is_recommended

    def generate_single(
        self, context: RoomContext
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Generate advice cho một phòng.

        Args:
            context: RoomContext của phòng.

        Returns:
            Tuple (advice_dict hoặc None, danh sách issues).
        """
        user_prompt = self._build_user_prompt(context)

        try:
            raw_response = self.connector.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
        except LLMConnectorError as e:
            logger.error("Room %d: LLM call failed - %s", context.room_id, e)
            return None, [str(e)]

        # Validate
        advice, issues = AdviceValidator.validate(raw_response, context)
        return advice, issues

    def generate_batch(
        self,
        csv_path: str,
        actions_path: Optional[str] = None,
        scores_path: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Generate advice cho toàn bộ CSV với cơ chế lưu tức thời và Resume.

        Args:
            csv_path: Đường dẫn file CSV input.
            actions_path: Đường dẫn file Actions CSV (tùy chọn).
            scores_path: Đường dẫn file Risk Scores CSV (tùy chọn).
            output_path: Đường dẫn file JSON output.

        Returns:
            Danh sách kết quả.
        """
        contexts = ContextBuilder.build_from_csv(csv_path, actions_path, scores_path)
        eligible = [c for c in contexts if self._should_process(c)]
        logger.info("Processing %d/%d eligible rooms", len(eligible), len(contexts))

        # 1. Load kết quả cũ nếu có (Cơ chế Resume)
        results: list[dict[str, Any]] = []
        existing_ids: set[int] = set()
        
        if output_path and Path(output_path).exists():
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    results = json.load(f)
                    existing_ids = {r["room_id"] for r in results if r["status"] == "success"}
                    logger.info("Resuming: Found %d existing advices in output file", len(existing_ids))
            except Exception as e:
                logger.warning("Could not load existing output for resume: %s", e)

        request_interval = 60.0 / API_REQUESTS_PER_MINUTE

        for i, ctx in enumerate(eligible, 1):
            # Bỏ qua nếu đã có advice (Resume)
            if ctx.room_id in existing_ids:
                continue

            logger.info("=== Room %d (%d/%d) ===", ctx.room_id, i, len(eligible))
            advice, issues = self.generate_single(ctx)

            result = {
                "room_id": ctx.room_id,
                "partner_id": ctx.partner_id,
                "discount_pct": ctx.discount_pct,
                "advice": advice,
                "issues": issues,
                "status": "success" if advice else "failed",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            results.append(result)

            # 2. Lưu NGAY LẬP TỨC sau mỗi phòng
            if output_path:
                try:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error("Failed to save intermediate result: %s", e)

            # Rate limiting
            if i < len(eligible):
                time.sleep(request_interval)

        # Summary
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info("=== COMPLETE: %d total advices saved ===", success_count)
        return results
