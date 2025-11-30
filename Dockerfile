# 1. THAY THẾ IMAGE SLIM BẰNG IMAGE FULL (Ổn định hơn cho CV/OCR)
FROM python:3.12 

# BƯỚC 1: CÀI ĐẶT THƯ VIỆN HỆ THỐNG (SYSTEM PACKAGES)
# Cài đặt Tesseract và OpenCV dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    # --- Tesseract và Ngôn ngữ ---
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    # Thư viện phát triển Tesseract và Leptonica (để đảm bảo liên kết)
    libtesseract-dev \
    libleptonica-dev \
    # --- Dependencies cho OpenCV (cv2) ---
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Dọn dẹp cache
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# BƯỚC KIỂM TRA: Xác nhận Tesseract đã được cài đặt và nằm trong $PATH
# (Bước này nên thành công 100% với image python:3.12)
RUN which tesseract
RUN tesseract --version 

# BƯỚC 2: CẤU HÌNH TESSDATA_PREFIX VÀ MÔI TRƯỜNG
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata

# BƯỚC 3: CÀI ĐẶT CODE VÀ THƯ VIỆN PYTHON
WORKDIR /app

# Sao chép và cài đặt các thư viện Python (từ requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code còn lại (web_server.py, ocr_app.py, thư mục static)
COPY . .

# BƯỚC 4: CHẠY DỊCH VỤ WEB
ENV PORT 10000
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
