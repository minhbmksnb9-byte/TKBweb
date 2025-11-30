# Sử dụng Python 3.9 Slim để nhẹ
FROM python:3.9-slim

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements trước để tận dụng cache của Docker
COPY requirements.txt .

# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào image
COPY . .

# Tạo thư mục static nếu chưa có để tránh lỗi permission
RUN mkdir -p static/uploads static/results

# Mở port (Render sẽ tự map port này thông qua biến $PORT)
EXPOSE 10000

# Chạy ứng dụng bằng Gunicorn
CMD ["gunicorn", "web_server:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]
