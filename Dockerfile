# Sử dụng base image Python 3.12 ổn định (Debian-based)
FROM python:3.12-slim

# BƯỚC 1: CÀI ĐẶT THƯ VIỆN HỆ THỐNG (SYSTEM PACKAGES)
# Cài đặt Tesseract và OpenCV dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    # --- Tesseract và Ngôn ngữ ---
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    # Thư viện xử lý ảnh cốt lõi cho Tesseract (Leptonica)
    libleptonica-dev \
    # --- Dependencies cho OpenCV (cv2) ---
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Dọn dẹp cache để giảm dung lượng image
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# BƯỚC KIỂM TRA: Xác nhận Tesseract đã được cài đặt và nằm trong $PATH
RUN which tesseract
RUN tesseract --version 

# BƯỚC 2: CẤU HÌNH TESSDATA_PREFIX VÀ MÔI TRƯỜNG
# Render/Docker sẽ dùng đường dẫn này để tìm data ngôn ngữ (.traineddata)
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata

# BƯỚC 3: CÀI ĐẶT CODE VÀ THƯ VIỆN PYTHON
WORKDIR /app

# Sao chép và cài đặt các thư viện Python (từ requirements.txt)
# Bao gồm pytesseract, opencv-python, numpy, Flask, gunicorn
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code còn lại (web_server.py, ocr_app.py, thư mục static)
COPY . .

# BƯỚC 4: CHẠY DỊCH VỤ WEB
# Đặt biến PORT Render sẽ sử dụng (thường là 10000)
ENV PORT 10000
# Lệnh chạy Gunicorn, trỏ tới file 'web_server.py' và đối tượng Flask 'app'
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
