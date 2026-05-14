import logging
import sys
import json
import os
from typing import List, Optional, Dict, Any

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

app = FastAPI(title="Phase 2 LLM Advice Engine API (v2.0)")

# --- Pydantic Models (V2 API Contract) ---

class Metrics(BaseModel):
    revenue: float = 0.0
    inquiry_count: int = 0
    occupancy_rate: float = 0.0
    conversion_rate: float = 0.0
    previous_revenue: float = 0.0
    reservation_count: int = 0

class Maturity(BaseModel):
    status: str = "unknown"
    room_age_days: int = 0

class Benchmarks(BaseModel):
    portfolio_avg_revenue: float = 0.0
    portfolio_avg_occupancy_rate: float = 0.0
    portfolio_avg_conversion_rate: float = 0.0

class PeerComparison(BaseModel):
    sample_size: int = 0
    price_gap: float = 0.0
    price_gap_pct: float = 0.0
    room_size_gap: float = 0.0
    benchmark_mode: str = ""
    benchmark_scope: str = ""
    benchmark_strength: str = ""

class SimulationFactors(BaseModel):
    price_gap_pct: float = 0.0
    benchmark_strength: str = ""
    anchor_revenue_used: float = 0.0
    primary_action: str = ""
    campaign_type: Optional[int] = None
    discount_targets: List[str] = []
    hybrid_metrics: dict = {}

class SimulationData(BaseModel):
    discount_pct: float = 0.0
    expected_revenue: float = 0.0
    confidence_score: float = 0.0
    is_recommended: bool = False
    simulation_type: str = ""
    simulation_factors: SimulationFactors

class ActionData(BaseModel):
    primary_action: str
    candidate_actions: List[dict]

class AdviceRequest(BaseModel):
    room_id: int
    partner_id: int
    metrics: Optional[Metrics] = Field(default_factory=Metrics)
    maturity: Optional[Maturity] = Field(default_factory=Maturity)
    benchmarks: Optional[Benchmarks] = Field(default_factory=Benchmarks)
    fee_snapshot: dict = {}
    peer_comparison: Optional[PeerComparison] = Field(default_factory=PeerComparison)
    simulation_data: SimulationData
    action_data: ActionData

# --- Khởi tạo AdviceGenerator ---
generator = AdviceGenerator()

@app.post("/api/v1/generate-advice")
async def generate_advice(request: AdviceRequest):
    if not generator:
         raise HTTPException(status_code=500, detail="AdviceGenerator not initialized")
    
    logger.info(">>> Processing V2 Advice Request for Room ID: %d", request.room_id)
    
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
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
