# Sử dụng Python 3.11 slim để giảm kích thước image
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (nếu có)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Tạo thư mục logs và data để tránh lỗi quyền truy cập
RUN mkdir -p logs data/output data/input

# Thiết lập biến môi trường mặc định
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Cổng API chạy (FastAPI mặc định)
EXPOSE 8000

# Chạy ứng dụng bằng Gunicorn với Uvicorn worker để tối ưu hiệu suất
# -w 4: Chạy 4 worker process (tùy chỉnh theo CPU server)
# -k uvicorn.workers.UvicornWorker: Sử dụng uvicorn worker cho FastAPI
CMD ["gunicorn", "api_service:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
