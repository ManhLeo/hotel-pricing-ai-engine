import logging
import sys
import json
from typing import List, Optional

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
    
    API này nhận dữ liệu phân tích từ Backend và sử dụng LLM để tạo ra các giải thích tự nhiên, 
    giúp người dùng hiểu rõ tại sao nên thực hiện các hành động Pricing nhất định.
    
    ### Các tính năng chính:
    * **Context Building**: Tự động xây dựng ngữ cảnh từ dữ liệu thô.
    * **Expert Advice Generation**: Sử dụng Gemini Flash để sinh lời khuyên chuyên sâu.
    * **Anti-Hallucination Validation**: Kiểm soát chặt chẽ số liệu đầu ra.
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
    sys.exit(1)

# --- Endpoints ---

@app.post("/api/v1/generate-advice")
async def generate_advice(request: AdviceRequest):
    """
    Endpoint nhận dữ liệu phòng và trả về lời khuyên từ chuyên gia AI.
    """
    logger.info(">>> Processing advice request for Room ID: %d", request.room_id)
    
    try:
        # 1. Chuyển đổi Pydantic model sang Dict
        payload = request.model_dump()
        
        # 2. Xây dựng Context từ Dict
        context = ContextBuilder.build_from_dict(payload)
        
        # 3. Gọi LLM để sinh lời khuyên
        advice, issues = generator.generate_single(context)
        
        if not advice:
            logger.error("LLM failed to generate advice for room %d", request.room_id)
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "LLM failed to generate advice",
                    "issues": issues
                }
            )
            
        logger.info("<<< Success: Advice generated for Room ID: %d", request.room_id)
        logger.info("Advice Content: %s", json.dumps(advice, ensure_ascii=False))
        return {
            "room_id": request.room_id,
            "partner_id": request.partner_id,
            "status": "success",
            "advice": advice,
            "issues": issues
        }
        
    except Exception as e:
        logger.exception("Unexpected error during advice generation: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Kiểm tra tình trạng sức khỏe của service."""
    return {
        "status": "healthy",
        "service": "llm-advice-engine",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    # Chạy server cục bộ để debug
    uvicorn.run(app, host="0.0.0.0", port=8000)
