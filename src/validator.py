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
        """Trích xuất JSON từ raw LLM response.

        LLM có thể trả về JSON bọc trong markdown code block,
        method này sẽ strip các ký tự thừa.

        Args:
            raw_text: Raw text từ LLM.

        Returns:
            Dict đã parse.

        Raises:
            ValidationError: Nếu không parse được JSON.
        """
        # Strip markdown code fences nếu có
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
        """Kiểm tra cấu trúc S.W.A.N có đầy đủ không.

        Args:
            advice: Dict đã parse từ LLM output.

        Returns:
            Danh sách lỗi (rỗng nếu hợp lệ).
        """
        errors: list[str] = []

        for field_name in REQUIRED_ADVICE_FIELDS:
            if field_name not in advice:
                errors.append(f"Missing required field: '{field_name}'")
            elif not isinstance(advice[field_name], str):
                errors.append(
                    f"Field '{field_name}' must be string, "
                    f"got {type(advice[field_name]).__name__}"
                )
            elif len(advice[field_name].strip()) == 0:
                errors.append(f"Field '{field_name}' is empty")

        return errors

    @staticmethod
    def extract_numbers_from_text(text: str) -> list[float]:
        """Trích xuất tất cả các số từ một đoạn text.

        Args:
            text: Đoạn text cần trích xuất.

        Returns:
            Danh sách các số tìm thấy.
        """
        # Match: 1,234.56 hoặc 1234.56 hoặc 12.5% (bỏ %)
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
        """Kiểm tra xem số liệu trong advice có khớp input không.

        So sánh các con số xuất hiện trong advice text với các giá trị
        đã biết từ RoomContext. Nếu có số lạ (không khớp bất kỳ field
        nào trong context), coi là hallucination.

        Args:
            advice: Dict advice đã parse.
            context: RoomContext gốc (ground truth).

        Returns:
            Danh sách cảnh báo (rỗng nếu OK).
        """
        warnings: list[str] = []

        # Tập hợp các số hợp lệ từ context
        valid_numbers: set[float] = {
            context.current_price,
            context.expected_revenue,
            context.price_gap_pct,
            abs(context.price_gap_pct),
            context.discount_pct,
            context.inquiry_uplift_pct,
            context.reservation_uplift_pct,
            context.revenue_uplift_pct,
            abs(context.revenue_uplift_pct),
            context.total_uplift_score,
            abs(context.total_uplift_score),
            context.confidence_score,
            context.anchor_revenue_used,
            context.total_effective_price_daily,
        }

        # Bổ sung các phí chi tiết vào tập hợp số hợp lệ
        if context.fee_structure_daily:
            for val in context.fee_structure_daily.values():
                if isinstance(val, (int, float)):
                    valid_numbers.add(float(val))

        if context.risk_score is not None:
            valid_numbers.add(context.risk_score)

        # Bổ sung các con số thời gian/tỷ lệ phổ biến trong tư vấn (7 ngày, 10 ngày, 14 ngày, 100%)
        valid_numbers.update({7.0, 10.0, 14.0, 21.0, 30.0, 100.0})

        # Loại bỏ các số quá nhỏ (1, 2, 3...) vì chúng xuất hiện
        # tự nhiên trong văn bản tiếng Việt
        valid_numbers = {n for n in valid_numbers if abs(n) >= 5}

        # Quét tất cả text trong advice
        full_text = " ".join(str(v) for v in advice.values())
        found_numbers = AdviceValidator.extract_numbers_from_text(full_text)

        for num in found_numbers:
            if abs(num) < 5:
                continue  # Bỏ qua số nhỏ

            # Kiểm tra xem số này có gần với bất kỳ số hợp lệ nào không
            is_valid = any(
                abs(num - valid) <= abs(valid) * MAX_NUMBER_DEVIATION_PCT
                for valid in valid_numbers
                if valid != 0
            )

            if not is_valid:
                warnings.append(
                    f"Suspicious number in advice: {num} "
                    f"(not found in input context)"
                )

        return warnings

    @staticmethod
    def validate(
        raw_text: str,
        context: RoomContext,
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Pipeline validation đầy đủ.

        Args:
            raw_text: Raw output từ LLM.
            context: RoomContext gốc để cross-check.

        Returns:
            Tuple (parsed_advice hoặc None, danh sách lỗi/cảnh báo).
        """
        all_issues: list[str] = []

        # Step 1: Parse JSON
        try:
            advice = AdviceValidator.parse_advice_json(raw_text)
        except ValidationError as e:
            return None, [str(e)]

        # Step 2: Check structure
        structure_errors = AdviceValidator.validate_structure(advice)
        all_issues.extend(structure_errors)

        # Step 3: Check numbers (chỉ warning, không reject)
        number_warnings = AdviceValidator.validate_numbers(advice, context)
        all_issues.extend(number_warnings)

        if structure_errors:
            logger.error(
                "Room %d: Validation FAILED - %s",
                context.room_id,
                structure_errors,
            )
            return None, all_issues

        if number_warnings:
            logger.warning(
                "Room %d: Passed with warnings - %s",
                context.room_id,
                number_warnings,
            )

        return advice, all_issues
