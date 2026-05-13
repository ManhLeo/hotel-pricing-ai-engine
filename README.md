# Phase 2: LLM Pricing Advice Engine (API Service)

## 📌 Tổng quan
Module **LLM Pricing Advice Engine** là trái tim của Phase 2, có nhiệm vụ chuyển đổi các dữ liệu số khô khan từ kết quả tính toán Pricing (Phase 1) thành những lời khuyên chuyên gia bằng ngôn ngữ tự nhiên. 

Hệ thống sử dụng mô hình **Gemini 1.5 Flash** (hoặc 2.0 Flash) để phân tích ngữ cảnh phòng, cấu trúc phí và các mục tiêu chiến dịch nhằm đưa ra giải thích minh bạch cho người dùng cuối.

## 🏗 Kiến trúc hệ thống
Hệ thống hiện tại hoạt động dưới dạng một **Internal API Service** (FastAPI), cho phép Backend tích hợp linh hoạt mà không cần thông qua file trung gian.

```
Phase_2_LLM_Engine/
├── api_service.py           # Entry point: FastAPI Service
├── src/
│   ├── llm_connector.py     # Layer 1: Kết nối low-level với Gemini API
│   ├── context_builder.py   # Layer 2: Chuyển đổi dữ liệu (CSV/JSON) sang Prompt Context
│   ├── advice_generator.py  # Layer 3: Điều phối (Orchestrator) toàn bộ luồng xử lý
│   └── validator.py         # Layer 4: Kiểm soát Hallucination (Chống bịa số liệu)
├── config/
│   └── settings.py          # Quản lý cấu hình (API Keys, Model Params)
├── prompts/
│   ├── system_prompt.md     # System Instruction cho AI
│   └── few_shot_examples.json # Ví dụ mẫu để AI học theo (Few-shot prompting)
├── requirements.txt         # Danh sách thư viện phụ thuộc
└── test_api_local.py        # Script test nhanh API cục bộ
```

## 🚀 Hướng dẫn khởi động

### 1. Cài đặt môi trường
```bash
# Tạo môi trường ảo
python -m venv venv
venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường
Tạo file `.env` từ file `.env.example` và điền `GEMINI_API_KEY` của bạn.

### 3. Chạy API Server
```bash
# Chạy server ở chế độ Production
python api_service.py

# Hoặc chạy bằng uvicorn (hỗ trợ hot-reload khi dev)
uvicorn api_service:app --host 0.0.0.0 --port 8000 --reload
```

## 🔌 API Documentation (Tài liệu tích hợp Backend)

### Endpoint chính: `POST /api/v1/generate-advice`
Hệ thống nhận dữ liệu chi tiết của một phòng và trả về lời khuyên chuyên gia.

**Request Payload (JSON):**
Tham khảo file mẫu tại `D:\INTERN\Hotel_Discount_AI\Table\old\input.json`. Cấu trúc bao gồm:
- `room_id`, `partner_id`
- `simulation_data`: Kết quả mô phỏng giảm giá.
- `action_data`: Các hành động khuyến nghị từ Rule-engine.
- `risk_score_data`: Cấu trúc phí chi tiết (Fee snapshot).

**Response (JSON):**
```json
{
  "room_id": 1,
  "status": "success",
  "advice": {
    "situation": "Phân tích tình hình hiện tại...",
    "why": "Giải thích lý do dựa trên số liệu phí...",
    "action": "Đề xuất cụ thể...",
    "next_steps": "Dự báo kết quả..."
  },
  "issues": []
}
```

## 🛡 Cơ chế Anti-Hallucination (Chống bịa số)
Điểm đặc biệt của Engine này là lớp **Validator (Layer 4)**. Mọi con số trong lời khuyên của AI đều được đối soát chéo với dữ liệu đầu vào:
- Nếu AI tự ý đưa ra một con số không có trong `fee_snapshot` hoặc `simulation_data`, hệ thống sẽ đánh dấu là `Suspicious number` trong trường `issues`.
- Điều này đảm bảo tính minh bạch và tin cậy tuyệt đối cho lời khuyên tài chính.

## 🛠 Tài liệu bổ sung
- **Swagger UI**: Khi server đang chạy, truy cập `http://127.0.0.1:8000/docs` để xem tài liệu API tương tác.
- **Coding Rules**: Các quy tắc phát triển mã nguồn nằm tại `CODING_RULES.md`.
