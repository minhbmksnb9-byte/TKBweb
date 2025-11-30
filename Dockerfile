# =========================================================
# GIAI ĐOẠN 1: TESSERACT BUILDER (Sử dụng Ubuntu ổn định hơn)
# Dùng image Ubuntu 22.04 để cài đặt Tesseract và các thư viện cần thiết.
# =========================================================
FROM ubuntu:22.04 AS tesseract-builder

# Cập nhật và cài đặt các gói hệ thống cần thiết
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    # Gói Tesseract chính và ngôn ngữ
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    # Các thư viện dùng chung cần thiết cho Tesseract
    libtesseract5 \
    libleptonica5 \
    # Các dependency của OpenCV (Tuyệt đối cần thiết khi copy)
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Kiểm tra (Debug) - Sẽ hiển thị trong Build Log
RUN which tesseract
RUN tesseract --version 


# =========================================================
# GIAI ĐOẠN 2: FINAL PYTHON RUNTIME (Môi trường chạy ứng dụng)
# Sử dụng image Python sạch và copy Tesseract đã cài đặt.
# =========================================================
FROM python:3.12 

# BƯỚC 1: COPY TESSERACT VÀ CÁC THƯ VIỆN CẦN THIẾT TỪ GIAI ĐOẠN 1

# Sao chép file thực thi Tesseract
COPY --from=tesseract-builder /usr/bin/tesseract /usr/bin/tesseract
# Sao chép các thư viện dùng chung quan trọng
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libtesseract.so.5 /usr/lib/x86_64-linux-gnu/
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libleptonica.so.5 /usr/lib/x86_64-linux-gnu/

# Sao chép dữ liệu ngôn ngữ
COPY --from=tesseract-builder /usr/share/tesseract-ocr/ /usr/share/tesseract-ocr/

# BƯỚC 2: CẤU HÌNH MÔI TRƯỜNG
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata
# Cập nhật dynamic linker cache để tìm thấy các thư viện dùng chung
RUN ldconfig

# BƯỚC 3: CÀI ĐẶT CODE VÀ THƯ VIỆN PYTHON
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# BƯỚC 4: CHẠY DỊCH VỤ WEB
ENV PORT 10000
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
