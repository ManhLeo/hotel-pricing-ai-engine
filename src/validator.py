"""
Validator - Layer 4: Anti-Hallucination & Output Quality

Trách nhiệm DUY NHẤT: Kiểm tra output của LLM có hợp lệ không.
- Đảm bảo cấu trúc JSON đúng (S.W.A.N framework)
- Đảm bảo LLM không bịa số liệu (cross-check với input data)
KHÔNG gọi API, KHÔNG sửa output.
"""

import json
import logging
import re
from typing import Any, Optional

from config.settings import MAX_NUMBER_DEVIATION_PCT, REQUIRED_ADVICE_FIELDS
from src.context_builder import RoomContext

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Lỗi khi output LLM không qua được validation."""
    pass


class AdviceValidator:
    """Kiểm tra chất lượng và tính chính xác của expert advice.

    Hai nhiệm vụ chính:
    1. Structure check: Đảm bảo có đủ 4 trường S.W.A.N.
    2. Number check: Đảm bảo con số trong advice khớp với input.
    """

    @staticmethod
    def parse_advice_json(raw_text: str) -> dict[str, Any]:
        """Trích xuất JSON từ raw LLM response."""
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Cannot parse LLM output as JSON: {e}\n"
                f"Raw output: {raw_text[:200]}..."
            )

    @staticmethod
    def validate_structure(advice: dict[str, Any]) -> list[str]:
        """Kiểm tra cấu trúc S.W.A.N có đầy đủ không."""
        errors: list[str] = []
        for field_name in REQUIRED_ADVICE_FIELDS:
            if field_name not in advice:
                errors.append(f"Missing required field: '{field_name}'")
            elif not isinstance(advice[field_name], str):
                errors.append(f"Field '{field_name}' must be string")
        return errors

    @staticmethod
    def extract_numbers_from_text(text: str) -> list[float]:
        """Trích xuất tất cả các số từ một đoạn text."""
        pattern = r"[-+]?\d[\d,]*\.?\d*"
        matches = re.findall(pattern, text)
        numbers: list[float] = []
        for m in matches:
            try:
                numbers.append(float(m.replace(",", "")))
            except ValueError:
                continue
        return numbers

    @staticmethod
    def validate_numbers(
        advice: dict[str, Any],
        context: RoomContext,
    ) -> list[str]:
        """Kiểm tra xem số liệu trong advice có khớp input không."""
        warnings: list[str] = []

        # Ground truth từ context
        valid_numbers = context.get_all_numeric_values()

        # Bổ sung các con số thời gian/tỷ lệ phổ biến (7 ngày, 10 ngày, 14 ngày, 100%)
        valid_numbers.update({7.0, 10.0, 14.0, 21.0, 30.0, 100.0})

        if context.risk_score is not None:
            valid_numbers.add(context.risk_score)

        # Quét tất cả text trong advice
        full_text = " ".join(str(v) for v in advice.values())
        found_numbers = AdviceValidator.extract_numbers_from_text(full_text)

        for num in found_numbers:
            if abs(num) < 5: continue

            is_valid = any(
                abs(num - valid) <= abs(valid) * MAX_NUMBER_DEVIATION_PCT
                for valid in valid_numbers if valid != 0
            )

            if not is_valid:
                warnings.append(f"Suspicious number in advice: {num}")

        return warnings

    @staticmethod
    def validate(
        raw_text: str,
        context: RoomContext,
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Pipeline validation đầy đủ."""
        all_issues: list[str] = []

        try:
            advice = AdviceValidator.parse_advice_json(raw_text)
        except ValidationError as e:
            return None, [str(e)]

        structure_errors = AdviceValidator.validate_structure(advice)
        all_issues.extend(structure_errors)

        number_warnings = AdviceValidator.validate_numbers(advice, context)
        all_issues.extend(number_warnings)

        if structure_errors:
            return None, all_issues

        return advice, all_issues
