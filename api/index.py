import logging
import sys
import json
import os
from typing import List, Optional, Dict

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.advice_generator import AdviceGenerator
from src.context_builder import ContextBuilder

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Phase 2 LLM Advice Engine API (v1.2)")

# --- Pydantic Models (Enhanced API Contract) ---

class RoomMetrics(BaseModel):
    inquiry_count: int = 0
    reservation_count: int = 0
    occupancy_rate: float = 0.0
    conversion_rate: float = 0.0
    revenue_30d: float = 0.0
    previous_revenue_30d: float = 0.0

class PeerComparison(BaseModel):
    sample_size: int = 0
    radius_km: float = 1.0
    room_price_per_day: float = 0.0
    peer_avg_price_per_day: float = 0.0
    price_gap_pct: float = 0.0

class SimulationFactors(BaseModel):
    price_gap_pct: float
    benchmark_strength: str
    anchor_revenue_used: float
    primary_action: str
    campaign_type: Optional[int] = None
    discount_targets: List[str] = []
    hybrid_metrics: dict = {}

class SimulationData(BaseModel):
    discount_pct: float
    expected_revenue: float
    confidence_score: float
    is_recommended: bool
    simulation_type: str
    simulation_factors: SimulationFactors

class ActionData(BaseModel):
    primary_action: str
    candidate_actions: List[dict]

class AdviceRequest(BaseModel):
    room_id: int
    partner_id: int
    room_metrics: Optional[RoomMetrics] = Field(default_factory=RoomMetrics)
    peer_comparison: Optional[PeerComparison] = Field(default_factory=PeerComparison)
    simulation_data: SimulationData
    action_data: ActionData
    risk_score_data: dict

# --- Khởi tạo AdviceGenerator ---
generator = AdviceGenerator()

@app.post("/api/v1/generate-advice")
async def generate_advice(request: AdviceRequest):
    if not generator:
         raise HTTPException(status_code=500, detail="AdviceGenerator not initialized")
    
    logger.info(">>> Processing Enhanced Advice Request for Room ID: %d", request.room_id)
    
    try:
        context = ContextBuilder.build_from_request(request)
        advice, issues = generator.generate_single(context)
        
        if not advice:
            raise HTTPException(status_code=500, detail={"error": "LLM failed", "issues": issues})
            
        return {
            "room_id": request.room_id,
            "partner_id": request.partner_id,
            "status": "success",
            "advice": advice,
            "issues": issues
        }
        
    except Exception as e:
        logger.exception("Error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
