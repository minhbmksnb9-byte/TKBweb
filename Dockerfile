# Dùng Python 3.9 slim
FROM python:3.9-slim

# Giảm file .pyc và bật log realtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cài đặt các thư viện hệ thống PaddleOCR cần
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Copy trước requirements để tận dụng cache build
COPY requirements.txt .

# Cài thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Tạo thư mục static để tránh lỗi permission
RUN mkdir -p static/uploads static/results

# Expose (Render dùng biến PORT nhưng EXPOSE để mô tả)
EXPOSE 10000

# Chạy bằng Gunicorn
CMD ["gunicorn", "web_server:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]
