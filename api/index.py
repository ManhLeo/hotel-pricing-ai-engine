import logging
import sys
import json
import os
from typing import List, Optional

# Thêm thư mục gốc vào sys.path để có thể import từ src và config
# Khi chạy trên Vercel, thư mục gốc là /var/task
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.advice_generator import AdviceGenerator
from src.context_builder import ContextBuilder

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Phase 2 LLM Advice Engine API",
    description="""
    ## Hệ thống sinh lời khuyên tối ưu hóa giá phòng (AI Expert Advice)
    """
)

# --- Pydantic Models (API Contract) ---

class SimulationFactors(BaseModel):
    price_gap_pct: float
    benchmark_strength: str
    anchor_revenue_used: float
    primary_action: str
    campaign_type: Optional[int] = None
    discount_targets: List[str] = []
    discount_target_scope: Optional[str] = None
    hybrid_metrics: dict = {}

class SimulationData(BaseModel):
    discount_pct: float
    expected_revenue: float
    confidence_score: float
    is_recommended: bool
    simulation_type: str
    simulation_factors: SimulationFactors

class ActionCandidate(BaseModel):
    type: str
    label: str

class ActionData(BaseModel):
    primary_action: str
    candidate_actions: List[ActionCandidate]

class FeeSnapshot(BaseModel):
    components_daily: dict
    total_effective_price_daily: float

class RiskScoreData(BaseModel):
    fee_snapshot: FeeSnapshot

class AdviceRequest(BaseModel):
    room_id: int
    partner_id: int
    simulation_data: SimulationData
    action_data: ActionData
    risk_score_data: RiskScoreData

# --- Khởi tạo AdviceGenerator (Singleton) ---
try:
    generator = AdviceGenerator()
    logger.info("AdviceGenerator initialized successfully for API service.")
except Exception as e:
    logger.error("Failed to initialize AdviceGenerator: %s", e)
    # Không exit trên Vercel để tránh vòng lặp crash
    generator = None

# --- Endpoints ---

@app.post("/api/v1/generate-advice")
async def generate_advice(request: AdviceRequest):
    if not generator:
         raise HTTPException(status_code=500, detail="AdviceGenerator not initialized")
         
    logger.info(">>> Processing advice request for Room ID: %d", request.room_id)
    
    try:
        payload = request.model_dump()
        context = ContextBuilder.build_from_dict(payload)
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
    return {
        "status": "healthy",
        "service": "llm-advice-engine",
        "version": "1.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
