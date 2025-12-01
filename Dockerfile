# Dockerfile (Đã chỉnh sửa)
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 🚀 Bổ sung các thư viện cần thiết cho OpenCV và hiển thị. 
# Tránh dùng libgl1 (GLX) nếu không có GPU/display, thay bằng libglvnd-dev nếu cần.
# Tuy nhiên, các package bạn đã chọn là phổ biến cho OpenCV trên môi trường không GUI.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    # ⚠️ Thay libgl1 bằng libglvnd-dev nếu gặp lỗi, nhưng ta giữ nguyên theo bạn
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# PaddlePaddle cần wheel nhiều, phải bật pip >= 23
RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ⚠️ TẠO THƯ MỤC CẦN THIẾT và đảm bảo quyền (dùng RUN)
# `mkdir -p` là tốt. `static` phải nằm trong `WORKDIR /app`
RUN mkdir -p static/uploads static/results 

# ⚠️ Đổi EXPOSE thành 10000 để khớp
EXPOSE 10000

# 🚀 Lệnh chạy Gunicorn
# - w 2: Dùng 2 worker để xử lý request đồng thời (có thể tăng/giảm)
# - b 0.0.0.0:10000: Bind tới cổng 10000 trên mọi interface
# - timeout 120: Tăng timeout cho các tác vụ nặng (OCR)
CMD ["gunicorn", "web_server:app", "--workers", "2", "--bind", "0.0.0.0:10000", "--timeout", "120"]
