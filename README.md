# Phase 2: LLM Pricing Advice Engine

## 📌 Tổng quan
Module **LLM Pricing Advice Engine** là trung tâm của Phase 2, có nhiệm vụ chuyển đổi dữ liệu pricing từ Phase 1 thành lời khuyên chuyên gia bằng ngôn ngữ tự nhiên.

Hệ thống hiện sử dụng mô hình qua **OpenRouter (OpenAI-compatible API)** để phân tích ngữ cảnh phòng, cấu trúc phí và mục tiêu chiến dịch, sau đó sinh advice có kiểm soát hallucination.

## 🏗 Kiến trúc hệ thống
Project hỗ trợ **2 cách chạy**:
1. **Internal API Service** (FastAPI) để backend gọi realtime.
2. **CLI batch mode** để xử lý CSV và xuất JSON.

```
Phase_2_LLM_Engine/
├── api/
│   └── index.py                 # FastAPI entrypoint
├── src/
│   ├── llm_connector.py         # Layer 1: Kết nối OpenRouter API
│   ├── context_builder.py       # Layer 2: Build RoomContext từ CSV/JSON
│   ├── advice_generator.py      # Layer 3: Orchestrator toàn bộ flow
│   └── validator.py             # Layer 4: Anti-hallucination & quality checks
├── config/
│   └── settings.py              # Cấu hình tập trung (API/model/threshold/logging)
├── prompts/
│   ├── system_prompt.md
│   └── few_shot_examples.json
├── data/
│   ├── input/
│   └── output/
├── tests/
│   └── test_validator.py
├── main.py                      # CLI entrypoint
├── requirements.txt
└── README.md
```

## 🚀 Hướng dẫn khởi động

### 1. Cài đặt môi trường
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường
Tạo file `.env` và khai báo tối thiểu:
```env
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=openai/gpt-oss-20b:free
LOG_LEVEL=INFO
```

> Các cấu hình khác xem tại `config/settings.py`.

---

## 🔌 Chạy API Service (FastAPI)

### Cách 1: Chạy bằng uvicorn (khuyến nghị)
```bash
uvicorn api.index:app --host 0.0.0.0 --port 8000 --reload
```

### Cách 2: chạy trực tiếp module
```bash
python api/index.py
```

### API chính
- `POST /api/v1/generate-advice`
- `GET /health`

### Swagger UI
Khi server chạy: `http://127.0.0.1:8000/docs`

---

## 🖥 Chạy CLI Batch

### Generate advice từ CSV
```bash
python main.py --input data/input/room_discount_simulations.csv
```

### Chỉ build context, không gọi LLM
```bash
python main.py --input data/input/room_discount_simulations.csv --dry-run
```

### Có thêm dữ liệu actions/scores
```bash
python main.py ^
  --input data/input/room_discount_simulations.csv ^
  --actions data/input/room_recommendation_actions.csv ^
  --scores data/input/room_risk_scores.csv ^
  --output data/output/advice.json
```

---

## 🛡 Cơ chế Anti-Hallucination
Lớp **Validator** (`src/validator.py`) kiểm tra:
1. **JSON structure**: phải có đủ 4 field bắt buộc (`situation`, `why`, `action`, `next_steps`).
2. **Number consistency**: đối soát số trong advice với dữ liệu đầu vào (`RoomContext`), cảnh báo `Suspicious number` nếu phát hiện số không hợp lệ.

Cơ chế này giúp tăng độ tin cậy và minh bạch của tư vấn tài chính.

## 🛠 Tài liệu bổ sung
- `CODING_RULES.md`: Quy tắc coding nội bộ.
- `tests/test_validator.py`: Unit test cho validator.
