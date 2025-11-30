# Sử dụng Python 3.9 Slim (bản nhẹ)
FROM python:3.9-slim

# Thiết lập biến môi trường để tránh Python tạo file .pyc và log mượt hơn
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cập nhật và cài đặt các gói hệ thống
# Lưu ý: 
# - Thay libgl1-mesa-glx bằng libgl1
# - Thêm tesseract-ocr-vie để hỗ trợ tiếng Việt
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy requirements trước để tận dụng cache
COPY requirements.txt .

# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Tạo thư mục static để tránh lỗi permission
RUN mkdir -p static/uploads static/results

# Mở port (Render sử dụng biến $PORT, nhưng EXPOSE để document)
EXPOSE 10000

# Chạy ứng dụng bằng Gunicorn
CMD ["gunicorn", "web_server:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]
