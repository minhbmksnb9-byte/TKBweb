# Dockerfile

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cài đặt các thư viện hệ thống cho OpenCV (dùng quyền root)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# 1. TẠO VÀ CHUYỂN SANG USER KHÔNG PHẢI ROOT 
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser 

# 2. Chạy pip với user không phải root
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy code
COPY --chown=appuser:appuser . .

# 4. Tạo thư mục kết quả (đảm bảo user appuser có quyền tạo)
RUN mkdir -p static/uploads static/results

EXPOSE 10000

# 5. Chạy Gunicorn: 
# workers=1 (chống OOM)
# timeout=300 (cho phép request đầu tiên có đủ thời gian tải model)
CMD ["gunicorn", "web_server:app", "--workers", "1", "--bind", "0.0.0.0:10000", "--timeout", "300"]
