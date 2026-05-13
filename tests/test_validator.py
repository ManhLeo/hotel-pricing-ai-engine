"""
Unit Tests for AdviceValidator

Chạy: python -m pytest tests/test_validator.py -v
"""

import json
import pytest

from src.context_builder import RoomContext
from src.validator import AdviceValidator, ValidationError


# ============================================================
# Fixtures
# ============================================================

def _make_context(**overrides) -> RoomContext:
    """Tạo RoomContext mẫu cho testing."""
    defaults = dict(
        room_id=6,
        partner_id=2,
        current_price=100_000,
        expected_revenue=120_000,
        price_gap_pct=45.0,
        discount_pct=5.0,
        inquiry_uplift_pct=12.8,
        reservation_uplift_pct=7.04,
        revenue_uplift_pct=3.8,
        total_uplift_score=3.80,
        confidence_score=90.0,
        is_recommended=True,
        anchor_revenue_used=120_000,
        primary_action="price_adjustment",
        benchmark_strength="medium",
    )
    defaults.update(overrides)
    return RoomContext(**defaults)


VALID_ADVICE_JSON = json.dumps({
    "situation": "Phong dang dat hon 45% so voi thi truong.",
    "why": "Muc giam 5% tang 12.8% luot quan tam.",
    "action": "Ap dung giam 5% tren tien thue.",
    "next_steps": "Theo doi trong 7-14 ngay.",
}, ensure_ascii=False)


# ============================================================
# Tests: parse_advice_json
# ============================================================

class TestParseAdviceJson:
    """Tests cho method parse_advice_json."""

    def test_parse_valid_json(self) -> None:
        result = AdviceValidator.parse_advice_json(VALID_ADVICE_JSON)
        assert "situation" in result
        assert "action" in result

    def test_parse_json_with_markdown_fences(self) -> None:
        wrapped = f"```json\n{VALID_ADVICE_JSON}\n```"
        result = AdviceValidator.parse_advice_json(wrapped)
        assert "situation" in result

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises(ValidationError):
            AdviceValidator.parse_advice_json("not a json {{{")


# ============================================================
# Tests: validate_structure
# ============================================================

class TestValidateStructure:
    """Tests cho method validate_structure."""

    def test_valid_structure_no_errors(self) -> None:
        advice = json.loads(VALID_ADVICE_JSON)
        errors = AdviceValidator.validate_structure(advice)
        assert len(errors) == 0

    def test_missing_field_returns_error(self) -> None:
        advice = {"situation": "ok", "why": "ok", "action": "ok"}
        # Missing "next_steps"
        errors = AdviceValidator.validate_structure(advice)
        assert any("next_steps" in e for e in errors)

    def test_empty_field_returns_error(self) -> None:
        advice = {
            "situation": "",
            "why": "ok",
            "action": "ok",
            "next_steps": "ok",
        }
        errors = AdviceValidator.validate_structure(advice)
        assert any("situation" in e for e in errors)


# ============================================================
# Tests: validate_numbers (Anti-Hallucination)
# ============================================================

class TestValidateNumbers:
    """Tests cho method validate_numbers."""

    def test_no_warnings_when_numbers_match(self) -> None:
        context = _make_context()
        advice = {
            "situation": "Phong dat hon 45% so voi thi truong.",
            "why": "Giam 5% tang 12.8% inquiry.",
            "action": "Ap dung giam 5%.",
            "next_steps": "Doanh thu tang 3.8%.",
        }
        warnings = AdviceValidator.validate_numbers(advice, context)
        assert len(warnings) == 0

    def test_warning_on_hallucinated_number(self) -> None:
        context = _make_context()
        advice = {
            "situation": "Phong dat hon 45% so voi thi truong.",
            "why": "Giam 5% tang 25.6% inquiry.",  # 25.6 is fabricated
            "action": "ok",
            "next_steps": "ok",
        }
        warnings = AdviceValidator.validate_numbers(advice, context)
        assert any("25.6" in w for w in warnings)


# ============================================================
# Tests: extract_numbers_from_text
# ============================================================

class TestExtractNumbers:
    """Tests cho method extract_numbers_from_text."""

    def test_extract_integers(self) -> None:
        nums = AdviceValidator.extract_numbers_from_text("tang 120000 dong")
        assert 120000.0 in nums

    def test_extract_decimals(self) -> None:
        nums = AdviceValidator.extract_numbers_from_text("tang 12.8%")
        assert 12.8 in nums

    def test_extract_formatted_numbers(self) -> None:
        nums = AdviceValidator.extract_numbers_from_text("doanh thu 2,100,000")
        assert 2100000.0 in nums

    def test_extract_negative(self) -> None:
        nums = AdviceValidator.extract_numbers_from_text("giam -3.8%")
        assert -3.8 in nums
