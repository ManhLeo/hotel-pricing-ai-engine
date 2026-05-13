"""
Context Builder - Layer 2: Chuẩn bị dữ liệu cho LLM

Trách nhiệm DUY NHẤT: Đọc CSV/JSON từ Phase 1, trích xuất các trường
cần thiết, và tạo structured context string cho prompt.
KHÔNG gọi API, KHÔNG mutate dữ liệu gốc.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoomContext:
    """Cấu trúc dữ liệu context cho một phòng.

    Immutable (frozen=True) để đảm bảo không bị mutate sau khi tạo.
    """

    # --- Identification ---
    room_id: int
    partner_id: int

    # --- Pricing ---
    current_price: float
    expected_revenue: float
    price_gap_pct: float

    # --- Risk ---
    risk_score: Optional[float] = None
    risk_reason: Optional[str] = None

    # --- Simulation ---
    discount_pct: float = 0.0
    inquiry_uplift_pct: float = 0.0
    reservation_uplift_pct: float = 0.0
    revenue_uplift_pct: float = 0.0
    total_uplift_score: float = 0.0
    confidence_score: float = 0.0
    is_recommended: bool = False

    # --- Domain (Phase 1.5 - Campaign Metadata) ---
    primary_action: str = ""
    campaign_type: Optional[str] = None
    discount_targets: list[str] = field(default_factory=list)
    discount_target_scope: Optional[str] = None
    simulation_type: Optional[str] = None
    benchmark_strength: str = "broad"

    # --- Anchor ---
    anchor_revenue_used: float = 0.0

    # --- Recommendation Label ---
    recommendation_label: str = ""

    # --- Fee Structure ---
    fee_structure_daily: dict = field(default_factory=dict)
    total_effective_price_daily: float = 0.0

    def get_all_numeric_values(self) -> set[float]:
        """Thu thập tất cả các giá trị số có trong context để phục vụ validation."""
        numbers = set()
        
        # Root level
        numbers.add(float(self.current_price))
        numbers.add(float(self.expected_revenue))
        numbers.add(float(self.price_gap_pct))
        numbers.add(float(self.anchor_revenue_used))
        numbers.add(float(self.confidence_score))
        
        # Simulation
        numbers.add(float(self.discount_pct))
        numbers.add(float(self.inquiry_uplift_pct))
        numbers.add(float(self.reservation_uplift_pct))
        numbers.add(float(self.revenue_uplift_pct))
        numbers.add(float(self.total_uplift_score))
        
        # Fees
        numbers.add(float(self.total_effective_price_daily))
        for val in self.fee_structure_daily.values():
            if isinstance(val, (int, float)):
                numbers.add(float(val))
        
        return numbers

    def to_prompt_text(self) -> str:
        """Chuyển context thành đoạn text có cấu trúc cho prompt.

        Returns:
            Chuỗi text mô tả trạng thái phòng.
        """
        lines = [
            f"=== ROOM {self.room_id} (Partner {self.partner_id}) ===",
            f"Current Price: {self.current_price:,.0f}",
            f"Revenue Before Discount (Anchor): {self.anchor_revenue_used:,.0f}",
            f"Price Gap vs Market: {self.price_gap_pct:+.1f}%",
            "",
            f"Proposed Action: {self.discount_pct}% Discount",
            f"  - Inquiry Uplift: +{self.inquiry_uplift_pct:.1f}%",
            f"  - Reservation Uplift: +{self.reservation_uplift_pct:.1f}%",
            f"  - Revenue Impact: {self.revenue_uplift_pct:+.1f}%",
            f"  - Expected Revenue After Action: {self.expected_revenue:,.0f}",
            f"  - Total Uplift Score: {self.total_uplift_score:+.2f}",
            "",
            f"Confidence Score: {self.confidence_score}/100",
            f"Benchmark Strength: {self.benchmark_strength}",
            f"Is Recommended: {'Yes' if self.is_recommended else 'No'}",
        ]

        # Domain metadata (nếu có)
        if self.primary_action:
            lines.append("")
            lines.append(f"Action Type: {self.primary_action}")
        if self.campaign_type:
            lines.append(f"Campaign Type: {self.campaign_type}")
        if self.discount_targets:
            lines.append(f"Discount Targets: {', '.join(self.discount_targets)}")
        if self.discount_target_scope:
            lines.append(f"Discount Scope: {self.discount_target_scope}")
        if self.simulation_type:
            lines.append(f"Simulation Type: {self.simulation_type}")

        # Risk context (nếu có)
        if self.risk_score is not None:
            lines.append("")
            lines.append(f"Risk Score: {self.risk_score:.1f}")
        if self.risk_reason:
            lines.append(f"Risk Reason: {self.risk_reason}")

        if self.recommendation_label:
            lines.append("")
            lines.append("=== RECOMMENDATION LABEL (RULE-BASED) ===")
            lines.append(f"Label: {self.recommendation_label}")

        if self.fee_structure_daily:
            lines.append("")
            lines.append("=== FEE BREAKDOWN (DAILY) ===")
            for fee_name, fee_val in self.fee_structure_daily.items():
                if isinstance(fee_val, (int, float)):
                    lines.append(f"{fee_name.replace('_', ' ').title()}: {fee_val:,.0f}")
                else:
                    lines.append(f"{fee_name.replace('_', ' ').title()}: {fee_val}")
            lines.append(f"Total Effective Price Daily: {self.total_effective_price_daily:,.0f}")

        return "\n".join(lines)


class ContextBuilder:
    """Xây dựng RoomContext từ dữ liệu CSV Phase 1.

    Đọc file CSV, parse JSON columns, và tạo danh sách RoomContext
    sẵn sàng cho LLM processing.
    """

    @staticmethod
    def _parse_simulation_factors(raw_json: str) -> dict[str, Any]:
        try:
            return json.loads(raw_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse simulation_factors_json: %s", e)
            return {}

    @staticmethod
    def _extract_action_label(primary_action: str, candidate_actions_json: str) -> str:
        if pd.isna(candidate_actions_json) or not candidate_actions_json:
            return ""
        try:
            candidates = json.loads(candidate_actions_json)
            for c in candidates:
                if c.get("type") == primary_action:
                    return c.get("label", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_fee_snapshot(features_json: str) -> tuple[dict, float]:
        if pd.isna(features_json) or not features_json:
            return {}, 0.0
        try:
            features = json.loads(features_json)
            fee_snapshot = features.get("fee_snapshot", {})
            return fee_snapshot.get("components_daily", {}), float(fee_snapshot.get("total_effective_price_daily", 0.0))
        except Exception:
            return {}, 0.0

    @staticmethod
    def build_from_row(row: pd.Series) -> RoomContext:
        factors = ContextBuilder._parse_simulation_factors(
            row.get("simulation_factors_json", "{}")
        )
        hybrid = factors.get("hybrid_metrics", {})
        anchor_rev = float(hybrid.get("anchor_revenue_used", 0))
        
        # Price = Anchor / 21 (dựa trên công thức 30 ngày * 70% lấp đầy ở Phase 1)
        calculated_price = anchor_rev / 21 if anchor_rev > 0 else 0

        # Extract Action Label
        primary_action = str(factors.get("primary_action", ""))
        merged_primary_action = row.get("primary_action_action", row.get("primary_action", primary_action))
        if pd.isna(merged_primary_action):
            merged_primary_action = primary_action
            
        candidate_actions = row.get("candidate_actions_json", "")
        recommendation_label = ContextBuilder._extract_action_label(merged_primary_action, candidate_actions)

        # Extract Fee Structure
        features_json = row.get("features_json", "")
        fee_structure_daily, total_effective_price_daily = ContextBuilder._extract_fee_snapshot(features_json)

        return RoomContext(
            room_id=int(row.get("room_id", 0)),
            partner_id=int(row.get("partner_id", 0)),
            current_price=calculated_price,
            expected_revenue=float(row.get("expected_revenue", 0)),
            price_gap_pct=float(factors.get("price_gap_pct", 0)),
            discount_pct=float(row.get("discount_pct", 0)),
            inquiry_uplift_pct=float(row.get("estimated_inquiry_uplift_pct", 0)),
            reservation_uplift_pct=float(row.get("estimated_reservation_uplift_pct", 0)),
            revenue_uplift_pct=float(row.get("estimated_revenue_uplift_pct", 0)),
            total_uplift_score=float(hybrid.get("total_uplift_score", 0)),
            anchor_revenue_used=anchor_rev,
            confidence_score=float(row.get("confidence_score", 0)),
            is_recommended=bool(int(row.get("is_recommended", 0))),
            primary_action=primary_action,
            campaign_type=factors.get("campaign_type"),
            discount_targets=factors.get("discount_targets", []),
            discount_target_scope=factors.get("discount_target_scope"),
            simulation_type=str(row.get("simulation_type", "")),
            benchmark_strength=str(factors.get("benchmark_strength", "broad")),
            recommendation_label=recommendation_label,
            fee_structure_daily=fee_structure_daily,
            total_effective_price_daily=total_effective_price_daily,
        )

    @staticmethod
    def build_from_dict(data: dict) -> RoomContext:
        """Tạo RoomContext từ JSON payload (Backend).

        Args:
            data: Dictionary chứa thông tin phòng (room_id, partner_id, simulation_data, action_data, risk_score_data).

        Returns:
            RoomContext instance.
        """
        sim_data = data.get("simulation_data", {})
        action_data = data.get("action_data", {})
        risk_data = data.get("risk_score_data", {})
        
        factors = sim_data.get("simulation_factors", {})
        hybrid = factors.get("hybrid_metrics", {})
        anchor_rev = float(factors.get("anchor_revenue_used", 0))
        
        # Price = Anchor / 21
        calculated_price = anchor_rev / 21 if anchor_rev > 0 else 0
        
        # Extract Action Label
        primary_action = str(factors.get("primary_action", ""))
        candidate_actions = action_data.get("candidate_actions", [])
        recommendation_label = ""
        for c in candidate_actions:
            if c.get("type") == primary_action:
                recommendation_label = c.get("label", "")
                break
                
        # Extract Fee Structure
        fee_snapshot = risk_data.get("fee_snapshot", {})
        fee_structure_daily = fee_snapshot.get("components_daily", {})
        total_effective_price_daily = float(fee_snapshot.get("total_effective_price_daily", 0.0))

        return RoomContext(
            room_id=int(data.get("room_id", 0)),
            partner_id=int(data.get("partner_id", 0)),
            current_price=calculated_price,
            expected_revenue=float(sim_data.get("expected_revenue", 0)),
            price_gap_pct=float(factors.get("price_gap_pct", 0)),
            discount_pct=float(sim_data.get("discount_pct", 0)),
            inquiry_uplift_pct=float(hybrid.get("estimated_inquiry_uplift_pct", 0)),
            reservation_uplift_pct=float(hybrid.get("estimated_reservation_uplift_pct", 0)),
            revenue_uplift_pct=float(hybrid.get("estimated_revenue_uplift_pct", 0)),
            total_uplift_score=float(hybrid.get("total_uplift_score", 0)),
            anchor_revenue_used=anchor_rev,
            confidence_score=float(sim_data.get("confidence_score", 0)),
            is_recommended=bool(sim_data.get("is_recommended", False)),
            primary_action=primary_action,
            campaign_type=factors.get("campaign_type"),
            discount_targets=factors.get("discount_targets", []),
            discount_target_scope=factors.get("discount_target_scope"),
            simulation_type=str(sim_data.get("simulation_type", "")),
            benchmark_strength=str(factors.get("benchmark_strength", "broad")),
            recommendation_label=recommendation_label,
            fee_structure_daily=fee_structure_daily,
            total_effective_price_daily=total_effective_price_daily,
        )

    @staticmethod
    def build_from_csv(filepath: str, actions_filepath: Optional[str] = None, scores_filepath: Optional[str] = None) -> list[RoomContext]:
        logger.info("Loading CSV: %s", filepath)
        df = pd.read_csv(filepath)
        logger.info("Loaded %d rows", len(df))

        if actions_filepath and Path(actions_filepath).exists():
            logger.info("Loading Actions CSV for labels: %s", actions_filepath)
            actions_df = pd.read_csv(actions_filepath)
            if "id" in actions_df.columns and "candidate_actions_json" in actions_df.columns:
                df = df.merge(
                    actions_df[["id", "primary_action", "candidate_actions_json"]],
                    left_on="room_recommendation_action_id",
                    right_on="id",
                    how="left",
                    suffixes=("", "_action")
                )
                logger.info("Merged candidate_actions_json into contexts.")
            else:
                logger.warning("Actions CSV missing 'id' or 'candidate_actions_json' columns.")

        if scores_filepath and Path(scores_filepath).exists():
            logger.info("Loading Risk Scores CSV for fees: %s", scores_filepath)
            scores_df = pd.read_csv(scores_filepath)
            if "room_id" in scores_df.columns and "features_json" in scores_df.columns:
                df = df.merge(
                    scores_df[["room_id", "features_json"]],
                    on="room_id",
                    how="left"
                )
                logger.info("Merged features_json into contexts.")
            else:
                logger.warning("Scores CSV missing 'room_id' or 'features_json' columns.")

        contexts: list[RoomContext] = []
        for _, row in df.iterrows():
            try:
                ctx = ContextBuilder.build_from_row(row)
                contexts.append(ctx)
            except Exception as e:
                logger.error(
                    "Failed to build context for row %s: %s",
                    row.get("id", "?"),
                    e,
                )

        logger.info("Built %d RoomContext objects", len(contexts))
        return contexts
