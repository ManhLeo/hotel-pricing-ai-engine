"""
Context Builder - Layer 2: Chuẩn bị dữ liệu cho LLM (v2.0)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomContext:
    """Cấu trúc dữ liệu context v2.0 (Rich Context)."""
    room_id: int
    partner_id: int
    
    # --- Actual Metrics ---
    metrics: Dict[str, Any] = field(default_factory=dict)
    maturity: Dict[str, Any] = field(default_factory=dict)
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    peer_comparison: Dict[str, Any] = field(default_factory=dict)
    fee_snapshot: Dict[str, Any] = field(default_factory=dict)

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
    
    # --- Contextual ---
    risk_score: Optional[float] = None
    recommendation_label: str = ""
    primary_action: str = ""
    anchor_revenue_used: float = 0.0

    # --- Derived Warnings ---
    high_one_time_fee_warning: str = ""

    def get_all_numeric_values(self) -> set[float]:
        """Thu thập số liệu cho validation."""
        numbers = {
            float(self.current_price), float(self.expected_revenue), 
            float(self.price_gap_pct), float(self.anchor_revenue_used), 
            float(self.confidence_score), float(self.discount_pct),
            float(self.inquiry_uplift_pct), float(self.reservation_uplift_pct),
            float(self.revenue_uplift_pct), float(self.total_uplift_score)
        }
        def extract_numbers(data: Any):
            if isinstance(data, dict):
                for v in data.values():
                    extract_numbers(v)
            elif isinstance(data, list):
                for v in data:
                    extract_numbers(v)
            elif isinstance(data, (int, float)) and not isinstance(data, bool):
                numbers.add(float(data))

        extract_numbers(self.metrics)
        extract_numbers(self.maturity)
        extract_numbers(self.benchmarks)
        extract_numbers(self.peer_comparison)
        extract_numbers(self.fee_snapshot)
        
        return numbers

    def to_prompt_text(self) -> str:
        """Chuyển context thành text chuyên nghiệp (Tích hợp Benchmarks & Fees)."""
        m = self.metrics
        b = self.benchmarks
        mat = self.maturity
        p = self.peer_comparison
        
        lines = [
            f"=== ROOM {self.room_id} (Partner {self.partner_id}) ===",
            "1. ROOM PROFILE & MATURITY:",
            f"   - Status: {mat.get('status', 'unknown').upper()} | Age: {mat.get('room_age_days', 0)} days",
            "",
            "2. PERFORMANCE vs PORTFOLIO (Last 30 Days):",
            f"   - Room Occupancy: {m.get('occupancy_rate', 0)*100:.1f}% vs Portfolio Avg: {b.get('portfolio_avg_occupancy_rate', 0)*100:.1f}%",
            f"   - Room Conversion: {m.get('conversion_rate', 0)*100:.1f}% vs Portfolio Avg: {b.get('portfolio_avg_conversion_rate', 0)*100:.1f}%",
            f"   - Room Revenue: {m.get('revenue', 0):,.0f} vs Portfolio Avg: {b.get('portfolio_avg_revenue', 0):,.0f}",
            f"   - Inquiries: {m.get('inquiry_count', 0)} | Reservations: {m.get('reservation_count', 0)}",
            "",
            "3. MARKET POSITIONING (Peer Comparison):",
            f"   - Sample Size: {p.get('sample_size', 0)} (Mode: {p.get('benchmark_scope', 'unknown')})",
            f"   - Price Gap: {p.get('price_gap_pct', 0):+.1f}% vs Market",
            f"   - Strength: {p.get('benchmark_strength', 'weak').upper()}",
            ""
        ]

        if self.high_one_time_fee_warning:
            lines.append("4. CRITICAL FRICTION POINT (FEE WARNING):")
            lines.append(f"   - {self.high_one_time_fee_warning}")
            lines.append("")

        lines.extend([
            f"{'5' if self.high_one_time_fee_warning else '4'}. PROPOSED STRATEGY (Simulation):",
            f"   - ACTION: {self.discount_pct}% Discount (MANDATORY: If 0, do not suggest any price reduction)",
            f"   - Type: {self.primary_action} ({self.recommendation_label})",
            f"   - Expected Inquiry Uplift: +{self.inquiry_uplift_pct:.1f}%",
            f"   - Expected Revenue Impact: {self.revenue_uplift_pct:+.1f}%",
            f"   - Confidence Score: {self.confidence_score}/100"
        ])
        
        return "\n".join(lines)


class ContextBuilder:
    """Xây dựng RoomContext đầy đủ thông tin (v2.0)."""

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
                
        # Phân tích One-time Fee vs Rent Fee (Tìm điểm nghẽn)
        fee_snap = request.fee_snapshot
        high_one_time_fee_warning = ""
        
        if fee_snap:
            daily_rent = float(fee_snap.get("recurring_components_daily", {}).get("rent_fee", 0))
            total_one_time = float(fee_snap.get("total_one_time_fee", 0))
            cleaning_fee = float(fee_snap.get("one_time_components", {}).get("cleaning_fee", 0))
            
            if daily_rent > 0 and total_one_time > daily_rent * 3:
                high_one_time_fee_warning = (
                    f"One-time fees ({total_one_time:,.0f}) are EXTREMELY HIGH compared to daily rent ({daily_rent:,.0f}). "
                    f"Cleaning fee alone is {cleaning_fee:,.0f}. This is a major booking barrier."
                )

        return RoomContext(
            room_id=request.room_id,
            partner_id=request.partner_id,
            metrics=request.metrics.model_dump() if request.metrics else {},
            maturity=request.maturity.model_dump() if request.maturity else {},
            benchmarks=request.benchmarks.model_dump() if request.benchmarks else {},
            peer_comparison=request.peer_comparison.model_dump() if request.peer_comparison else {},
            fee_snapshot=fee_snap,
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
            high_one_time_fee_warning=high_one_time_fee_warning,
        )
