import os
from dotenv import load_dotenv
from openai import OpenAI

# Load cấu hình
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free") # Dùng Llama 3 free để test cho ổn định

def test_connection():
    print(f"--- ĐANG TEST KẾT NỐI OPENROUTER ---")
    print(f"Model: {OPENROUTER_MODEL}")
    
    if not OPENROUTER_API_KEY:
        print("❌ Lỗi: Chưa tìm thấy OPENROUTER_API_KEY trong file .env")
        return

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://localhost", 
                "X-Title": "Local Test Script",
            },
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Connection Successful' in English and Vietnamese."},
            ],
        )
        print("✅ Kết nối thành công!")
        print(f"AI phản hồi: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Kết nối thất bại: {str(e)}")

if __name__ == "__main__":
    test_connection()
