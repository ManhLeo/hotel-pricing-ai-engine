# ============================================================
# CODING RULES - Phase 2 LLM Engine
# Mọi contributor PHẢI tuân thủ các quy tắc dưới đây.
# ============================================================

# 1. NGÔN NGỮ & PHIÊN BẢN
# --------------------------------------------------------
# - Python >= 3.11
# - Type hints BẮT BUỘC cho mọi function signature
# - Docstring BẮT BUỘC cho mọi class và public method (Google style)
# - Encoding: UTF-8 cho mọi file

# 2. CẤU TRÚC MODULE
# --------------------------------------------------------
# - Mỗi file trong src/ chỉ chứa MỘT class chính
# - Tên file = snake_case, tên class = PascalCase
# - Không import trực tiếp từ file khác bằng đường dẫn tương đối sâu
#   Đúng:  from src.llm_connector import LLMConnector
#   Sai:   from src.llm_connector import LLMConnector as LC

# 3. ERROR HANDLING
# --------------------------------------------------------
# - Không dùng bare except (except:)
# - Luôn log lỗi trước khi raise
# - Sử dụng custom exception class cho domain errors
# - Retry logic phải có max_retries và exponential backoff

# 4. LOGGING
# --------------------------------------------------------
# - Sử dụng module logging chuẩn, KHÔNG dùng print()
# - Log levels:
#   DEBUG   = Chi tiết prompt/response (chỉ dev)
#   INFO    = Tiến trình xử lý (room X done, batch complete)
#   WARNING = Fallback logic activated, data missing
#   ERROR   = API fail, validation fail
# - Format: [%(asctime)s] %(levelname)s %(name)s: %(message)s

# 5. DATA FLOW
# --------------------------------------------------------
# CSV (Phase 1) → ContextBuilder → LLMConnector → Validator → Output
#
# - ContextBuilder: Chỉ đọc data, KHÔNG mutate
# - LLMConnector:   Chỉ gọi API, KHÔNG xử lý logic nghiệp vụ
# - Validator:      Chỉ kiểm tra output, KHÔNG gọi API
# - Mỗi layer KHÔNG được biết chi tiết implementation của layer khác

# 6. PROMPT MANAGEMENT
# --------------------------------------------------------
# - System prompt lưu trong prompts/system_prompt.md (plain text)
# - Few-shot examples lưu trong prompts/few_shot_examples.json
# - KHÔNG hardcode prompt trong source code
# - Mọi thay đổi prompt phải có version comment

# 7. TESTING
# --------------------------------------------------------
# - Mỗi module trong src/ phải có test tương ứng trong tests/
# - Test naming: test_<method_name>_<scenario>
# - Mock API calls, KHÔNG gọi API thật trong test
# - Chạy: python -m pytest tests/ -v

# 8. SECURITY
# --------------------------------------------------------
# - API key KHÔNG BAO GIỜ commit vào git
# - Sử dụng .env + python-dotenv
# - File .env phải nằm trong .gitignore
# - Chỉ commit .env.example (không chứa key thật)

# 9. OUTPUT FORMAT
# --------------------------------------------------------
# - Expert advice trả về dạng JSON có cấu trúc cố định
# - Các trường bắt buộc: situation, why, action, next_steps
# - Mọi con số trong advice PHẢI khớp với input data (anti-hallucination)
# - Validator sẽ reject output nếu phát hiện số liệu không khớp

# 10. GIT WORKFLOW
# --------------------------------------------------------
# - Branch naming: feature/<tên>, fix/<tên>, refactor/<tên>
# - Commit message: <type>: <mô tả ngắn>
#   Ví dụ: feat: add campaign-aware context builder
#          fix: handle empty discount_targets array
#          refactor: extract retry logic to decorator
