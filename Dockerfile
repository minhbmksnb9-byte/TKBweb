# Bước 1: Chọn hệ điều hành cơ sở với Python 3.12
# (Bạn có thể đổi 3.12-slim thành 3.13-slim nếu muốn thử,
# nhưng 3.12 sẽ ổn định hơn)
FROM python:3.12-slim

# Bước 2: Cập nhật và cài đặt Tesseract + gói ngôn ngữ
# Chúng ta cài 'tesseract-ocr' (engine) và 'tesseract-ocr-vie' (Tiếng Việt)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
 && rm -rf /var/lib/apt/lists/*

# Bước 3: (Tùy chọn) Đặt biến môi trường TESSDATA
# Chỉ định nơi Tesseract tìm file ngôn ngữ đã cài
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata

# Bước 4: Cài đặt code ứng dụng
WORKDIR /app

# Sao chép file requirements.txt trước để tận dụng cache của Docker
COPY requirements.txt .

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code của bạn vào thư mục /app
COPY . .

# Bước 5: Lệnh để chạy ứng dụng
# Render sẽ tự động cung cấp biến $PORT (thường là 10000)
# 'app:app' nghĩa là: tìm file 'app.py' và chạy đối tượng 'app' (của Flask)
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
