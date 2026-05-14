"""
Context Builder - Layer 2: Chuẩn bị dữ liệu cho LLM (Enhanced Version)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomContext:
    """Cấu trúc dữ liệu context đầy đủ cho Expert Advice."""
    room_id: int
    partner_id: int
    
    # --- Actual Metrics (Added) ---
    room_metrics: Dict[str, Any] = field(default_factory=dict)
    peer_comparison: Dict[str, Any] = field(default_factory=dict)

    # --- Pricing & Simulation ---
    current_price: float = 0.0
    discount_pct: float = 0.0
    expected_revenue: float = 0.0
    price_gap_pct: float = 0.0
    
    # --- Results ---
    inquiry_uplift_pct: float = 0.0
    reservation_uplift_pct: float = 0.0
    revenue_uplift_pct: float = 0.0
    total_uplift_score: float = 0.0
    confidence_score: float = 0.0
    is_recommended: bool = False
    
    # --- Risk (Added back for Validator compatibility) ---
    risk_score: Optional[float] = None
    risk_reason: Optional[str] = None
    
    # --- Contextual ---
    recommendation_label: str = ""
    primary_action: str = ""
    anchor_revenue_used: float = 0.0
    fee_structure_daily: dict = field(default_factory=dict)
    total_effective_price_daily: float = 0.0

    def get_all_numeric_values(self) -> set[float]:
        """Thu thập số liệu cho validation."""
        numbers = {
            float(self.current_price), float(self.expected_revenue), 
            float(self.price_gap_pct), float(self.anchor_revenue_used), 
            float(self.confidence_score), float(self.discount_pct),
            float(self.inquiry_uplift_pct), float(self.reservation_uplift_pct),
            float(self.revenue_uplift_pct), float(self.total_uplift_score)
        }
        # Add metrics numbers
        for v in self.room_metrics.values():
            if isinstance(v, (int, float)): numbers.add(float(v))
        # Add peer numbers
        for v in self.peer_comparison.values():
            if isinstance(v, (int, float)): numbers.add(float(v))
        return numbers

    def to_prompt_text(self) -> str:
        """Chuyển context thành text chuyên nghiệp cho LLM."""
        m = self.room_metrics
        p = self.peer_comparison
        
        lines = [
            f"=== ROOM {self.room_id} (Partner {self.partner_id}) ===",
            "1. CURRENT PERFORMANCE (Last 30 Days):",
            f"   - Occupancy: {m.get('occupancy_rate', 0)*100:.1f}% | Conversion: {m.get('conversion_rate', 0)*100:.1f}%",
            f"   - Inquiries: {m.get('inquiry_count', 0)} | Reservations: {m.get('reservation_count', 0)}",
            f"   - Revenue: {m.get('revenue_30d', 0):,.0f} (Previous: {m.get('previous_revenue_30d', 0):,.0f})",
            "",
            "2. MARKET POSITIONING (Peer Comparison):",
            f"   - Sample Size: {p.get('sample_size', 0)} rooms within {p.get('radius_km', 0)}km",
            f"   - Room Price: {p.get('room_price_per_day', 0):,.0f} | Peer Avg: {p.get('peer_avg_price_per_day', 0):,.0f}",
            f"   - Price Gap: {p.get('price_gap_pct', 0):+.1f}% vs Market",
            "",
            "3. PROPOSED STRATEGY (Simulation):",
            f"   - ACTION: {self.discount_pct}% Discount (MANDATORY: If 0, do not suggest any price reduction)",
            f"   - Type: {self.primary_action} ({self.recommendation_label})",
            f"   - Expected Inquiry Uplift: +{self.inquiry_uplift_pct:.1f}%",
            f"   - Expected Revenue Impact: {self.revenue_uplift_pct:+.1f}%",
            f"   - Confidence Score: {self.confidence_score}/100"
        ]
        return "\n".join(lines)


class ContextBuilder:
    """Xây dựng RoomContext đầy đủ thông tin."""

    @staticmethod
    def build_from_request(request: Any) -> RoomContext:
        sim = request.simulation_data
        factors = sim.simulation_factors
        hybrid = factors.hybrid_metrics
        action = request.action_data
        
        anchor_rev = float(factors.anchor_revenue_used)
        primary_action = factors.primary_action
        
        # Match label
        recommendation_label = ""
        for c in action.candidate_actions:
            if c.get("type") == primary_action:
                recommendation_label = c.get("label", "")
                break
                
        # Fee & Risk
        risk_data = request.risk_score_data
        fee_snap = risk_data.get("fee_snapshot", {})
        risk_score = risk_data.get("risk_score")

        return RoomContext(
            room_id=request.room_id,
            partner_id=request.partner_id,
            risk_score=risk_score,
            room_metrics=request.room_metrics.model_dump() if request.room_metrics else {},
            peer_comparison=request.peer_comparison.model_dump() if request.peer_comparison else {},
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
            fee_structure_daily=fee_snap.get("components_daily", {}),
            total_effective_price_daily=fee_snap.get("total_effective_price_daily", 0.0),
        )
