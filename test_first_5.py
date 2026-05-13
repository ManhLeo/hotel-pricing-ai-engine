import json
import logging
import sys

from src.advice_generator import AdviceGenerator
from src.context_builder import ContextBuilder

# Cấu hình logging cơ bản để dễ đọc trên terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    print("\n" + "="*60)
    print("🚀 Bắt đầu test API sinh Advice cho 5 phòng đầu tiên")
    print("="*60 + "\n")
    
    csv_path = "data/input/room_discount_simulations.csv"
    actions_path = "data/input/room_recommendation_actions.csv"
    scores_path = "data/input/room_risk_scores.csv"

    # 1. Build Context
    contexts = ContextBuilder.build_from_csv(csv_path, actions_path, scores_path)
    
    generator = AdviceGenerator()
    eligible = [c for c in contexts if generator._should_process(c)]
    
    print(f"\n=> Tìm thấy {len(eligible)} phòng cần phân tích. Sẽ test {min(5, len(eligible))} phòng đầu tiên...\n")
    
    results = []
    
    # 2. Chạy API thật cho 5 phòng đầu tiên
    for ctx in eligible[:5]:
        print("="*50)
        print(f"🔍 Testing Room ID: {ctx.room_id} (Partner {ctx.partner_id})")
        print("="*50)
        
        # In nhanh Prompt text để review lại
        print("\n--- Ngữ cảnh cung cấp cho LLM (Prompt) ---")
        print(ctx.to_prompt_text())
        print("------------------------------------------")
        
        # Gọi LLM (API call thật)
        print("\nĐang gọi API Gemini...")
        advice, issues = generator.generate_single(ctx)
        
        if advice:
            print("\n✅ KIỂM TRA OUTPUT TỪ LLM:")
            print(json.dumps(advice, ensure_ascii=False, indent=2))
            
            if issues:
                print("\n⚠️ WARNING TỪ VALIDATOR (Nếu có lỗi format hoặc bịa số):")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ VALIDATOR: PASS 100% (Không phát hiện Hallucination)")
        else:
            print("\n❌ GỌI API THẤT BẠI:")
            if issues:
                print(f"  - Lỗi: {issues}")
        
        # Lưu kết quả
        results.append({
            "room_id": ctx.room_id,
            "advice": advice,
            "issues": issues,
            "status": "success" if advice else "failed"
        })
        print("\n")

    # 3. Lưu toàn bộ kết quả test ra file
    output_file = "data/output/test_5_results.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("="*60)
    print(f"🎉 Test hoàn tất! Kết quả đã được lưu tại: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()
