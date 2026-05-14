"""
Context Builder - Layer 2: Chuẩn bị dữ liệu cho LLM (Super-Lite Version)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomContext:
    """Cấu trúc dữ liệu context cho một phòng (Immutable)."""
    room_id: int
    partner_id: int
    current_price: float
    expected_revenue: float
    price_gap_pct: float
    risk_score: Optional[float] = None
    risk_reason: Optional[str] = None
    discount_pct: float = 0.0
    inquiry_uplift_pct: float = 0.0
    reservation_uplift_pct: float = 0.0
    revenue_uplift_pct: float = 0.0
    total_uplift_score: float = 0.0
    confidence_score: float = 0.0
    is_recommended: bool = False
    primary_action: str = ""
    campaign_type: Optional[str] = None
    discount_targets: list[str] = field(default_factory=list)
    discount_target_scope: Optional[str] = None
    simulation_type: Optional[str] = None
    benchmark_strength: str = "broad"
    anchor_revenue_used: float = 0.0
    recommendation_label: str = ""
    fee_structure_daily: dict = field(default_factory=dict)
    total_effective_price_daily: float = 0.0

    def get_all_numeric_values(self) -> set[float]:
        """Thu thập số liệu cho validation (Cực nhanh với set comprehension)."""
        numbers = {
            float(self.current_price), float(self.expected_revenue), 
            float(self.price_gap_pct), float(self.anchor_revenue_used), 
            float(self.confidence_score), float(self.discount_pct),
            float(self.inquiry_uplift_pct), float(self.reservation_uplift_pct),
            float(self.revenue_uplift_pct), float(self.total_uplift_score),
            float(self.total_effective_price_daily)
        }
        # Thêm phí nếu có
        if self.fee_structure_daily:
            numbers.update(float(v) for v in self.fee_structure_daily.values() if isinstance(v, (int, float)))
        return numbers

    def to_prompt_text(self) -> str:
        """Chuyển context thành text (Tối ưu hóa f-string)."""
        return (
            f"=== ROOM {self.room_id} (Partner {self.partner_id}) ===\n"
            f"Current Price: {self.current_price:,.0f}\n"
            f"Revenue Before Discount: {self.anchor_revenue_used:,.0f}\n"
            f"Price Gap: {self.price_gap_pct:+.1f}%\n\n"
            f"Proposed: {self.discount_pct}% Discount\n"
            f" - Inquiry Uplift: +{self.inquiry_uplift_pct:.1f}%\n"
            f" - Reservation Uplift: +{self.reservation_uplift_pct:.1f}%\n"
            f" - Revenue Impact: {self.revenue_uplift_pct:+.1f}%\n"
            f" - Score: {self.total_uplift_score:+.2f}\n\n"
            f"Confidence: {self.confidence_score}/100 | Label: {self.recommendation_label}"
        )


class ContextBuilder:
    """Xây dựng RoomContext - Đã lược bỏ mọi logic dư thừa."""

    @staticmethod
    def build_from_request(request: Any) -> RoomContext:
        """Nạp trực tiếp từ Pydantic Request (Không cần model_dump)."""
        sim = request.simulation_data
        factors = sim.simulation_factors
        hybrid = factors.hybrid_metrics
        action = request.action_data
        risk = request.risk_score_data
        
        anchor_rev = float(factors.anchor_revenue_used)
        
        # Extract Label
        primary_action = factors.primary_action
        recommendation_label = ""
        for c in action.candidate_actions:
            if c.type == primary_action:
                recommendation_label = c.label
                break
                
        # Fee
        fee_snap = risk.fee_snapshot

        return RoomContext(
            room_id=request.room_id,
            partner_id=request.partner_id,
            current_price=anchor_rev / 21 if anchor_rev > 0 else 0,
            expected_revenue=sim.expected_revenue,
            price_gap_pct=factors.price_gap_pct,
            discount_pct=sim.discount_pct,
            inquiry_uplift_pct=hybrid.get("estimated_inquiry_uplift_pct", 0),
            reservation_uplift_pct=hybrid.get("estimated_reservation_uplift_pct", 0),
            revenue_uplift_pct=hybrid.get("estimated_revenue_uplift_pct", 0),
            total_uplift_score=hybrid.get("total_uplift_score", 0),
            anchor_revenue_used=anchor_rev,
            confidence_score=sim.confidence_score,
            is_recommended=sim.is_recommended,
            primary_action=primary_action,
            recommendation_label=recommendation_label,
            fee_structure_daily=fee_snap.components_daily,
            total_effective_price_daily=fee_snap.total_effective_price_daily,
        )
